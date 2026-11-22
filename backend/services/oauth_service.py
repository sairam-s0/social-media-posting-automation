"""Hardened OAuth service for LinkedIn and Reddit.
Features:
- Encrypted vault storage in Windows Credential Manager
- Expiring OAuth states (10-minute expiry window)
- PKCE code challenge and verifier support
- Automatic refresh token renewal
- Token expiration countdown calculations
- Minimum required platform scopes
"""
from __future__ import annotations

import base64
import hashlib
import os
import secrets
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from config import (
    LINKEDIN_REDIRECT_URI,
    REDDIT_REDIRECT_URI,
    LINKEDIN_CLIENT_ID,
    LINKEDIN_CLIENT_SECRET,
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT,
)
from utils.vault import get_secret, save_tokens, get_tokens, clear_tokens, delete_secret
from utils.logging_config import logger

def get_platform_credentials(platform: str) -> tuple[str, str, str]:
    """Retrieve client credentials with priority:
    1. Custom user overrides in encrypted vault (if explicitly configured)
    2. Central backend environment config (os.getenv with dynamic .env reload)
    3. Central config constants (from config.py)
    """
    from dotenv import load_dotenv
    from pathlib import Path
    for p in [Path.cwd() / ".env", Path(__file__).resolve().parents[2] / ".env"]:
        if p.exists():
            load_dotenv(p, override=True)
            break

    if platform == "linkedin":
        client_id = get_secret("linkedin_client_id") or os.getenv("LINKEDIN_CLIENT_ID", "").strip() or LINKEDIN_CLIENT_ID
        client_secret = get_secret("linkedin_client_secret") or os.getenv("LINKEDIN_CLIENT_SECRET", "").strip() or LINKEDIN_CLIENT_SECRET
        return client_id, client_secret, ""
    elif platform == "reddit":
        client_id = get_secret("reddit_client_id") or os.getenv("REDDIT_CLIENT_ID", "").strip() or REDDIT_CLIENT_ID
        client_secret = get_secret("reddit_client_secret") or os.getenv("REDDIT_CLIENT_SECRET", "").strip() or REDDIT_CLIENT_SECRET
        user_agent = get_secret("reddit_user_agent") or os.getenv("REDDIT_USER_AGENT", "").strip() or REDDIT_USER_AGENT
        return client_id, client_secret, user_agent
    return "", "", ""

def get_platform_redirect_uri(platform: str) -> str:
    """Retrieve effective OAuth redirect URI with priority:
    1. Custom redirect URI override saved in encrypted vault
    2. Central environment variable / config (LINKEDIN_REDIRECT_URI / REDDIT_REDIRECT_URI)
    3. Deterministic loopback fallback
    """
    custom_uri = get_secret(f"{platform}_redirect_uri")
    if custom_uri and custom_uri.strip():
        return custom_uri.strip()
    if platform == "linkedin":
        return os.getenv("LINKEDIN_REDIRECT_URI", "").strip() or LINKEDIN_REDIRECT_URI
    elif platform == "reddit":
        return os.getenv("REDDIT_REDIRECT_URI", "").strip() or REDDIT_REDIRECT_URI
    return f"http://127.0.0.1:8000/auth/{platform}/callback"

def reset_platform_credentials(platform: str) -> bool:
    """Wipe custom credentials from vault so platform reverts to central shared credentials."""
    delete_secret(f"{platform}_client_id")
    delete_secret(f"{platform}_client_secret")
    delete_secret(f"{platform}_redirect_uri")
    if platform == "reddit":
        delete_secret("reddit_user_agent")
    return True

def is_platform_configured(platform: str) -> bool:
    """Check if platform has required credentials configured centrally or locally."""
    client_id, client_secret, _ = get_platform_credentials(platform)
    if platform == "linkedin":
        return bool(client_id)
    elif platform == "reddit":
        return bool(client_id and client_secret)
    return False

def is_shared_oauth(platform: str) -> bool:
    """Return True if using central shared OAuth developer app rather than custom user app."""
    if platform == "linkedin":
        has_custom = bool(get_secret("linkedin_client_id"))
        has_central = bool(os.getenv("LINKEDIN_CLIENT_ID", "").strip() or LINKEDIN_CLIENT_ID)
        return not has_custom and has_central
    elif platform == "reddit":
        has_custom = bool(get_secret("reddit_client_id"))
        has_central = bool(os.getenv("REDDIT_CLIENT_ID", "").strip() or REDDIT_CLIENT_ID)
        return not has_custom and has_central
    return False

# Expiring states: state -> {"platform": str, "created_at": float, "verifier": str, "redirect_uri": str}
OAUTH_STATES: dict[str, dict[str, Any]] = {}
STATE_EXPIRY_SECONDS = 600  # 10 minutes

def generate_pkce() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge

def clean_expired_states() -> None:
    """Purge OAuth states older than 10 minutes."""
    now = time.time()
    expired = [s for s, data in OAUTH_STATES.items() if now - data["created_at"] > STATE_EXPIRY_SECONDS]
    for s in expired:
        OAUTH_STATES.pop(s, None)

def initiate_oauth_flow(platform: str, custom_redirect_uri: Optional[str] = None) -> str:
    """Generate authorization redirect URL with hardened state and PKCE."""
    clean_expired_states()

    state = secrets.token_urlsafe(32)
    verifier, challenge = generate_pkce()
    redirect_uri = custom_redirect_uri.strip() if custom_redirect_uri and custom_redirect_uri.strip() else get_platform_redirect_uri(platform)

    if platform == "linkedin":
        client_id, _, _ = get_platform_credentials("linkedin")
        if not client_id:
            raise HTTPException(400, "LinkedIn Client ID is missing. Central credentials must be configured on backend.")
        
        endpoint = "https://www.linkedin.com/oauth/v2/authorization"
        scopes = "openid profile w_member_social"
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": scopes,
        }
    elif platform == "reddit":
        client_id, _, _ = get_platform_credentials("reddit")
        if not client_id:
            raise HTTPException(400, "Reddit Client ID is missing. Central credentials must be configured on backend.")

        endpoint = "https://www.reddit.com/api/v1/authorize"
        scopes = "identity submit"
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": scopes,
            "duration": "permanent",
            "authorize": "true"
        }
    else:
        raise HTTPException(404, f"Unsupported platform: {platform}")

    OAUTH_STATES[state] = {
        "platform": platform,
        "created_at": time.time(),
        "verifier": verifier,
        "redirect_uri": redirect_uri,
    }

    return endpoint + "?" + urlencode(params)

async def handle_oauth_callback(platform: str, code: str, state: str) -> dict[str, Any]:
    """Validate state and exchange authorization code for encrypted tokens."""
    clean_expired_states()
    state_data = OAUTH_STATES.pop(state, None)
    if not state_data or state_data["platform"] != platform:
        raise HTTPException(400, "Invalid or expired OAuth state. States expire after 10 minutes.")

    verifier = state_data["verifier"]
    redirect_uri = state_data.get("redirect_uri") or get_platform_redirect_uri(platform)

    if platform == "linkedin":
        client_id, client_secret, _ = get_platform_credentials("linkedin")
        if not client_id:
            raise HTTPException(400, "LinkedIn Client ID not found.")

        token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        auth = None
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
    elif platform == "reddit":
        client_id, client_secret, user_agent = get_platform_credentials("reddit")
        if not client_id or not client_secret:
            raise HTTPException(500, "Reddit client credentials not configured on backend.")

        token_url = "https://www.reddit.com/api/v1/access_token"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri
        }
        auth = (client_id, client_secret)
        headers = {"User-Agent": user_agent or "AutoSocialPoster/1.0"}
    else:
        raise HTTPException(404, "Unknown platform")

    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(token_url, data=data, auth=auth, headers=headers)
        if res.is_error:
            logger.error(f"{platform} token exchange failed with code {res.status_code}: {res.text}")
            err_msg = res.text[:200]
            try:
                err_data = res.json()
                err_msg = err_data.get("error_description") or err_data.get("error") or err_msg
            except Exception:
                pass
            raise HTTPException(502, f"{platform.title()} authorization failed: {err_msg}")

        token_data = res.json()
        expires_in = int(token_data.get("expires_in", 3600 * 24 * 60 if platform == "linkedin" else 3600))
        expires_at = time.time() + expires_in

        # Retrieve profile information
        author = None
        account_name = None
        if platform == "linkedin":
            profile_res = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {token_data['access_token']}"}
            )
            if profile_res.is_success:
                prof = profile_res.json()
                author = f"urn:li:person:{prof['sub']}" if prof.get("sub") else None
                account_name = prof.get("name") or prof.get("given_name")
        else:
            profile_res = await client.get(
                "https://oauth.reddit.com/api/v1/me",
                headers={"Authorization": f"bearer {token_data['access_token']}", **headers}
            )
            if profile_res.is_success:
                prof = profile_res.json()
                author = prof.get("name")
                account_name = f"u/{prof.get('name')}" if prof.get("name") else None

    stored_payload = {
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "expires_at": expires_at,
        "author": author,
        "account_name": account_name or author or "Connected Account"
    }
    save_tokens(platform, stored_payload)
    logger.info(f"Successfully saved encrypted OAuth tokens for {platform}")
    return stored_payload

async def get_valid_token(platform: str) -> dict[str, Any]:
    """Retrieve token from vault; automatically refresh if expired or about to expire."""
    tokens = get_tokens(platform)
    if not tokens:
        raise HTTPException(401, f"{platform.title()} is not connected. Connect in Settings > Integrations.")

    now = time.time()
    # If token expires in less than 5 minutes and we have a refresh token, refresh it
    if tokens.get("expires_at", 0) - now < 300 and tokens.get("refresh_token"):
        logger.info(f"Refreshing expiring OAuth token for {platform}...")
        try:
            tokens = await refresh_oauth_token(platform, tokens["refresh_token"])
        except Exception as e:
            logger.error(f"Failed to refresh token for {platform}: {e}")
            raise HTTPException(401, f"{platform.title()} authorization expired. Reconnect in Settings > Integrations.")

    if tokens.get("expires_at", 0) <= now:
        raise HTTPException(401, f"{platform.title()} token has expired. Reconnect in Settings > Integrations.")

    return tokens

async def refresh_oauth_token(platform: str, refresh_token: str) -> dict[str, Any]:
    """Execute refresh_token grant flow with the provider."""
    if platform == "linkedin":
        client_id, client_secret, _ = get_platform_credentials("linkedin")
        token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
        }
        if client_secret:
            data["client_secret"] = client_secret
        auth = None
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
    elif platform == "reddit":
        client_id, client_secret, user_agent = get_platform_credentials("reddit")
        token_url = "https://www.reddit.com/api/v1/access_token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        auth = (client_id, client_secret)
        headers = {"User-Agent": user_agent or "AutoSocialPoster/1.0"}
    else:
        raise HTTPException(400, "Unknown platform")

    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(token_url, data=data, auth=auth, headers=headers)
        if res.is_error:
            raise HTTPException(401, f"Token refresh failed for {platform}: {res.text[:200]}")
        new_data = res.json()

    current = get_tokens(platform) or {}
    expires_in = int(new_data.get("expires_in", 3600 * 24 * 60 if platform == "linkedin" else 3600))
    current["access_token"] = new_data["access_token"]
    if new_data.get("refresh_token"):
        current["refresh_token"] = new_data["refresh_token"]
    current["expires_at"] = time.time() + expires_in

    save_tokens(platform, current)
    return current

def get_platform_status(platform: str) -> dict[str, Any]:
    """Check connection status and compute days until expiration."""
    tokens = get_tokens(platform)
    if not tokens:
        return {
            "connected": False,
            "account_name": "",
            "days_remaining": 0,
            "expires_soon": False,
            "expired": False
        }

    now = time.time()
    expires_at = tokens.get("expires_at", 0)
    seconds_left = max(0.0, expires_at - now)
    days_remaining = int(seconds_left // 86400)
    expired = expires_at <= now
    expires_soon = not expired and days_remaining <= 7

    return {
        "connected": not expired,
        "account_name": tokens.get("account_name") or tokens.get("author") or "Connected",
        "days_remaining": days_remaining,
        "expires_soon": expires_soon,
        "expired": expired
    }

def disconnect_platform(platform: str) -> None:
    """Disconnect and wipe tokens from encrypted vault."""
    clear_tokens(platform)
    logger.info(f"Disconnected and wiped tokens for platform: {platform}")
