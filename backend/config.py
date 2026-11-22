"""Configuration module for AutoSocial Poster.
Stores all runtime data (database, logs, locks) in %APPDATA%/AutoSocialPoster,
binds to 127.0.0.1 only, and generates a random per-session token at launch.
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path

import sys
from pathlib import Path
from dotenv import load_dotenv

# Search for and load .env files from project root, cwd, and config directory
dotenv_candidates = [
    Path.cwd() / ".env",
    Path(__file__).resolve().parents[1] / ".env",
]
for p in dotenv_candidates:
    if p.exists():
        load_dotenv(p)

# Application branding & directories
APP_NAME = "AutoSocial Poster"
APP_IDENTIFIER = "AutoSocialPoster"

# Locate AppData directory (%APPDATA%/AutoSocialPoster on Windows)
if os.name == "nt":
    BASE_APPDATA = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
else:
    BASE_APPDATA = Path.home() / ".config"

APP_DATA_DIR = BASE_APPDATA / APP_IDENTIFIER
DATA_DIR = APP_DATA_DIR / "data"
LOGS_DIR = APP_DATA_DIR / "logs"
CONFIG_DIR = APP_DATA_DIR / "config"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# Also load .env from user config dir if present
if (CONFIG_DIR / ".env").exists():
    load_dotenv(CONFIG_DIR / ".env")

# Database path in AppData
DATABASE_PATH = DATA_DIR / "social_automation.sqlite3"
LOG_FILE_PATH = LOGS_DIR / "social_media_poster.log"
LOCK_FILE_PATH = APP_DATA_DIR / "app.lock"

# Project root & Frontend static dist
if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass and (Path(meipass) / "dist").exists():
        FRONTEND_DIST = Path(meipass) / "dist"
    elif (PROJECT_ROOT / "_internal" / "dist").exists():
        FRONTEND_DIST = PROJECT_ROOT / "_internal" / "dist"
    elif (PROJECT_ROOT / "dist").exists():
        FRONTEND_DIST = PROJECT_ROOT / "dist"
    else:
        FRONTEND_DIST = PROJECT_ROOT / "_internal" / "dist"
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    FRONTEND_DIST = PROJECT_ROOT / "dist"

# Fixed host & port for deterministic OAuth redirect callbacks
HOST = "127.0.0.1"
PORT = int(os.getenv("PORT", "8000"))

# OAuth Redirect URIs (must match Developer App registration exactly)
LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI", f"http://127.0.0.1:{PORT}/auth/linkedin/callback")
REDDIT_REDIRECT_URI = os.getenv("REDDIT_REDIRECT_URI", f"http://127.0.0.1:{PORT}/auth/reddit/callback")

# Centrally configured Shared OAuth Developer Credentials (Backend Only)
# Secrets remain secure on backend / host and are never embedded in the packaged client binary
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "").strip()
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "").strip()

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "").strip()
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "").strip()
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "AutoSocialPoster/1.0 (Shared OAuth by u/AutoSocialOfficial)").strip()

# Security & Session Token
# Generated freshly at backend launch to authenticate all API requests
SESSION_TOKEN = secrets.token_hex(32)

# Safety & Limits
DAILY_POST_CAP = int(os.getenv("DAILY_POST_CAP", "5"))
MAX_INPUT_TOPIC_LENGTH = 500
MAX_INPUT_MESSAGE_LENGTH = 2000
MAX_INPUT_AUDIENCE_LENGTH = 500
MAX_INPUT_REFERENCE_LENGTH = 4000
MAX_SCHEDULE_DAYS = 7
DUPLICATE_CHECK_WINDOW_DAYS = 7
MISSED_POST_THRESHOLD_HOURS = 2

# Production flags
ALLOW_SIMULATED_PUBLISH = False
IS_PRODUCTION = os.getenv("APP_ENV", "production").lower() != "development"
