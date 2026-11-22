"""SQLite Database module storing runtime state in %APPDATA%/AutoSocialPoster/data/social_automation.sqlite3.
"""
from __future__ import annotations

import sqlite3
from typing import Generator
from config import DATABASE_PATH
from utils.logging_config import logger

def get_db() -> sqlite3.Connection:
    """Create a new SQLite connection with thread safety and dictionary row factory."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db() -> None:
    """Initialize database tables with safe migrations."""
    logger.info(f"Initializing database at: {DATABASE_PATH}")
    with get_db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            topic TEXT NOT NULL,
            platform TEXT NOT NULL,
            destination TEXT,
            subreddit TEXT,
            content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            approved INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            scheduled_at TEXT,
            published_at TEXT,
            external_id TEXT,
            error TEXT,
            timezone TEXT
        )""")

        # Safe migrations for posts table
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(posts)").fetchall()}
        if "destination" not in cols:
            conn.execute("ALTER TABLE posts ADD COLUMN destination TEXT")
        if "scheduled_at" not in cols:
            conn.execute("ALTER TABLE posts ADD COLUMN scheduled_at TEXT")
        if "timezone" not in cols:
            conn.execute("ALTER TABLE posts ADD COLUMN timezone TEXT")

        conn.commit()
