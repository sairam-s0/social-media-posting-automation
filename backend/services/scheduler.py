"""Background scheduler service for AutoSocial Poster.
Handles:
- Startup catch-up safety (marks posts older than threshold as 'missed' for user review)
- 7-day future window enforcement
- Continuous polling loop for scheduled dispatches
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from config import MAX_SCHEDULE_DAYS, MISSED_POST_THRESHOLD_HOURS
from database.db import get_db
from services.publisher_service import publish_post_idempotent
from utils.logging_config import logger

def validate_schedule_time(scheduled_at_str: str) -> str:
    """Validate that scheduled_at is ISO 8601, not in past, and strictly within the next 7 days."""
    try:
        clean_str = scheduled_at_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
    except Exception:
        raise HTTPException(400, "Invalid scheduled_at datetime format. Provide an ISO 8601 string.")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    now_utc = datetime.now(timezone.utc)
    # 45s clock skew buffer for past check
    if dt < now_utc - timedelta(seconds=45):
        raise HTTPException(400, "Scheduled date/time cannot be in the past.")

    # Strictly enforce 7-day limit (with 1-hour timezone boundary allowance)
    max_window = now_utc + timedelta(days=MAX_SCHEDULE_DAYS, hours=1)
    if dt > max_window:
        raise HTTPException(
            400,
            f"Scheduled time must be within the next {MAX_SCHEDULE_DAYS} days. "
            f"Dates beyond {MAX_SCHEDULE_DAYS} days are strictly not allowed."
        )

    return dt.astimezone(timezone.utc).isoformat()

async def handle_startup_catchup():
    """Evaluate posts scheduled before startup. Mark stale posts as 'missed' to prompt user."""
    logger.info("Evaluating scheduled queue for startup catch-up...")
    now_utc = datetime.now(timezone.utc)
    threshold = timedelta(hours=MISSED_POST_THRESHOLD_HOURS)

    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, scheduled_at, topic, platform FROM posts WHERE status = 'scheduled' AND scheduled_at IS NOT NULL"
        ).fetchall()

    for row in rows:
        try:
            sched_dt = datetime.fromisoformat(row["scheduled_at"].replace("Z", "+00:00"))
            if sched_dt.tzinfo is None:
                sched_dt = sched_dt.replace(tzinfo=timezone.utc)

            if sched_dt <= now_utc:
                delay = now_utc - sched_dt
                if delay > threshold:
                    # Stale post: Mark as missed for explicit user review
                    hours_late = round(delay.total_seconds() / 3600, 1)
                    reason = f"Missed scheduled dispatch ({hours_late} hrs late while app was closed). Review and publish manually or reschedule."
                    logger.warning(f"Post {row['id']} ({row['platform']}) marked as 'missed': {reason}")
                    with get_db() as conn:
                        conn.execute("UPDATE posts SET status = 'missed', error = ? WHERE id = ?", (reason, row["id"]))
                        conn.commit()
                else:
                    # Within acceptable window: dispatch now
                    logger.info(f"Catching up recently due post {row['id']}...")
                    await publish_post_idempotent(row["id"])
        except Exception as ex:
            logger.error(f"Error handling startup catch-up for post {row['id']}: {ex}")

async def scheduler_worker_loop():
    """Background publisher worker polling continuously for due posts."""
    await handle_startup_catchup()

    while True:
        try:
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT id, scheduled_at FROM posts WHERE status = 'scheduled' AND scheduled_at IS NOT NULL"
                ).fetchall()

            now_utc = datetime.now(timezone.utc)
            for row in rows:
                try:
                    sched_dt = datetime.fromisoformat(row["scheduled_at"].replace("Z", "+00:00"))
                    if sched_dt.tzinfo is None:
                        sched_dt = sched_dt.replace(tzinfo=timezone.utc)

                    if sched_dt <= now_utc:
                        logger.info(f"Scheduled post {row['id']} is due for publication. Dispatching...")
                        await publish_post_idempotent(row["id"])
                except Exception as ex:
                    logger.error(f"Failed to auto-publish post {row['id']}: {ex}")
                    # Error state handled in publisher_service
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Scheduler worker error: {e}")

        await asyncio.sleep(10)
