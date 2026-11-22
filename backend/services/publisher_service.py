"""Publishing service enforcing platform safety rules, idempotency locks,
rate limiting, exponential backoff, and duplicate-content protection.
"""
from __future__ import annotations

import asyncio
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict

import httpx
from fastapi import HTTPException
from config import DAILY_POST_CAP, DUPLICATE_CHECK_WINDOW_DAYS, ALLOW_SIMULATED_PUBLISH
from database.db import get_db
from services.oauth_service import get_valid_token
from utils.vault import get_secret
from utils.logging_config import logger

def normalize_text(text: str) -> str:
    """Normalize text for duplicate content comparisons."""
    return re.sub(r"\s+", " ", text.strip().lower())

def check_daily_post_cap(platform: str) -> None:
    """Ensure platform daily post quota has not been exceeded."""
    with get_db() as conn:
        row = conn.execute(
            """SELECT COUNT(*) as cnt FROM posts 
               WHERE platform = ? AND status = 'published' 
               AND date(published_at) = date('now')""",
            (platform,)
        ).fetchone()
        count = row["cnt"] if row else 0

    if count >= DAILY_POST_CAP:
        logger.warning(f"Daily post limit reached for {platform} ({count}/{DAILY_POST_CAP})")
        raise HTTPException(
            429,
            f"Daily publication limit reached ({DAILY_POST_CAP} posts/day on {platform.title()}). "
            f"Please wait until tomorrow to prevent spam flags and account bans."
        )

def check_duplicate_content(platform: str, content: str, exclude_post_id: str) -> None:
    """Check for duplicate content published in the last 7 days."""
    norm_target = normalize_text(content)
    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT id, content FROM posts 
                WHERE platform = ? AND status = 'published' AND id != ?
                AND published_at >= datetime('now', '-{DUPLICATE_CHECK_WINDOW_DAYS} days')""",
            (platform, exclude_post_id)
        ).fetchall()

    for row in rows:
        norm_existing = normalize_text(row["content"])
        if norm_target == norm_existing:
            raise HTTPException(
                400,
                f"Duplicate content detected! Identical text was already published to {platform.title()} "
                f"within the last {DUPLICATE_CHECK_WINDOW_DAYS} days."
            )

def escape_linkedin_text(text: str) -> str:
    """Escape LinkedIn little-text reserved characters so commentary isn't truncated."""
    return re.sub(r'([\\|{}@\[\]()<>~_*])', r'\\\1', text)

async def post_to_linkedin_with_backoff(content: str, author_urn: str, access_token: str) -> str:
    """Publish to LinkedIn REST API with retry and backoff on 429."""
    url = "https://api.linkedin.com/rest/posts"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "LinkedIn-Version": "202602",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }
    payload = {
        "author": author_urn,
        "commentary": escape_linkedin_text(content),
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    retries = 3
    backoff = 2.0

    async with httpx.AsyncClient(timeout=45.0) as client:
        for attempt in range(1, retries + 1):
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After", backoff))
                logger.warning(f"LinkedIn rate limited (429). Backing off for {retry_after}s (attempt {attempt}/{retries})")
                await asyncio.sleep(retry_after)
                backoff *= 2.0
                continue

            if response.is_error:
                logger.error(f"LinkedIn publishing failed (Status {response.status_code}): {response.text[:200]}")
                raise HTTPException(502, f"LinkedIn rejected post: {response.text[:200]}")

            external_id = response.headers.get("x-restli-id", "")
            return external_id

    raise HTTPException(429, "LinkedIn rate limit exceeded after retries.")

async def post_to_reddit_with_backoff(content: str, destination: str, access_token: str) -> str:
    """Publish to Reddit API with retry and backoff on 429."""
    url = "https://oauth.reddit.com/api/submit"
    user_agent = get_secret("reddit_user_agent") or os.getenv("REDDIT_USER_AGENT", "AutoSocialPoster/1.0")

    parts = content.split("\n", 1)
    raw_title = parts[0].removeprefix("Title:").strip()
    title = raw_title if raw_title else "Update"
    body = parts[1].strip() if len(parts) > 1 else ""
    target_sr = (destination or "smallbusiness").removeprefix("r/")

    headers = {
        "Authorization": f"bearer {access_token}",
        "User-Agent": user_agent,
    }
    data = {
        "sr": target_sr,
        "kind": "self",
        "title": title,
        "text": body,
        "api_type": "json",
    }

    retries = 3
    backoff = 2.0

    async with httpx.AsyncClient(timeout=45.0) as client:
        for attempt in range(1, retries + 1):
            response = await client.post(url, headers=headers, data=data)
            if response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After", backoff))
                logger.warning(f"Reddit rate limited (429). Backing off for {retry_after}s (attempt {attempt}/{retries})")
                await asyncio.sleep(retry_after)
                backoff *= 2.0
                continue

            if response.is_error:
                logger.error(f"Reddit publishing failed: {response.text[:200]}")
                raise HTTPException(502, f"Reddit rejected submission: {response.text[:200]}")

            try:
                res_data = response.json()
                errors = res_data.get("json", {}).get("errors", [])
                if errors:
                    raise HTTPException(502, f"Reddit API error: {errors}")
                external_id = res_data.get("json", {}).get("data", {}).get("id", "")
                return external_id
            except (ValueError, KeyError) as e:
                raise HTTPException(502, f"Invalid response from Reddit: {e}")

    raise HTTPException(429, "Reddit rate limit exceeded after retries.")

async def publish_post_idempotent(post_id: str) -> Dict[str, Any]:
    """Atomically publish post with publishing lock preventing duplicate dispatches."""
    # Step 1: Check existing post
    with get_db() as conn:
        post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        raise HTTPException(404, "Post not found.")

    if post["status"] == "published":
        return {
            "id": post_id,
            "status": "published",
            "external_id": post["external_id"],
            "published_at": post["published_at"],
            "message": "Post was already published."
        }

    # Step 2: Atomic publishing lock transition
    with get_db() as conn:
        cur = conn.execute(
            """UPDATE posts SET status = 'publishing', error = NULL 
               WHERE id = ? AND status IN ('draft', 'scheduled', 'failed', 'missed')""",
            (post_id,)
        )
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(409, "Post is already currently in publishing lock or published.")

    platform = post["platform"]
    content = post["content"]
    destination = post["destination"] or post["subreddit"] or ""

    try:
        # Step 3: Platform Rules & Safeguards
        check_daily_post_cap(platform)
        check_duplicate_content(platform, content, post_id)

        # Step 4: OAuth Verification & Fresh Token
        token_info = await get_valid_token(platform)
        access_token = token_info["access_token"]

        # Step 5: Dispatch to Platform API
        if platform == "linkedin":
            author = token_info.get("author")
            if not author:
                raise HTTPException(400, "LinkedIn user profile identity is missing. Reconnect in Settings.")
            external_id = await post_to_linkedin_with_backoff(content, author, access_token)
        elif platform == "reddit":
            external_id = await post_to_reddit_with_backoff(content, destination, access_token)
        else:
            raise HTTPException(400, f"Unsupported platform: {platform}")

        # Step 6: Mark Published
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            conn.execute(
                """UPDATE posts SET status = 'published', approved = 1, 
                   published_at = ?, external_id = ?, error = NULL WHERE id = ?""",
                (now_iso, external_id, post_id)
            )
            conn.commit()

        logger.info(f"Successfully published post {post_id} to {platform} (External ID: {external_id})")
        return {
            "id": post_id,
            "status": "published",
            "approved": True,
            "external_id": external_id,
            "published_at": now_iso
        }

    except Exception as exc:
        err_msg = str(exc.detail if isinstance(exc, HTTPException) else exc)
        logger.error(f"Publication failed for post {post_id}: {err_msg}")
        with get_db() as conn:
            conn.execute(
                "UPDATE posts SET status = 'failed', error = ? WHERE id = ?",
                (err_msg, post_id)
            )
            conn.commit()
        raise exc
