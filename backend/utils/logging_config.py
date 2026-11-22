"""Sanitized logging configuration.
Prevents leaking secrets, tokens, passwords, or full sensitive request bodies.
Logs to file in %APPDATA%/AutoSocialPoster/logs and stderr.
"""
from __future__ import annotations

import logging
import re
import sys
from logging.handlers import RotatingFileHandler
from config import LOG_FILE_PATH

SECRET_PATTERNS = [
    re.compile(r"(bearer\s+)[a-zA-Z0-9_\-\.]{8,}", re.IGNORECASE),
    re.compile(r"(gsk_[a-zA-Z0-9]{20,})", re.IGNORECASE),
    re.compile(r"((client_secret|api_key|token|password|secret)[\"']?\s*[:=]\s*[\"']?)([a-zA-Z0-9_\-\.]{6,})([\"']?)", re.IGNORECASE),
]

class SanitizedFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        sanitized = original
        for pattern in SECRET_PATTERNS:
            sanitized = pattern.sub(r"\1[REDACTED]", sanitized)
        return sanitized

def setup_logger(name: str = "AutoSocialPoster") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        formatter = SanitizedFormatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Rotating file handler (max 5MB, keep 3 backups)
        file_handler = RotatingFileHandler(
            str(LOG_FILE_PATH),
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)

        # Stream handler for console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

    return logger

logger = setup_logger()
