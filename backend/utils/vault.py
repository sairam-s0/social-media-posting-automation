"""Encrypted credential vault using Windows Credential Manager / DPAPI via the keyring library.
Never stores secrets, passwords, or OAuth tokens in plaintext in SQLite or .env.
"""
from __future__ import annotations

import json
import keyring
from typing import Any, Optional
from utils.logging_config import logger

VAULT_SERVICE = "AutoSocialPoster"

def save_secret(key: str, value: str) -> None:
    """Save secret encrypted in the OS credential vault."""
    try:
        keyring.set_password(VAULT_SERVICE, key, value)
    except Exception as e:
        logger.error(f"Failed to save secret '{key}' to keyring vault: {e}")
        raise RuntimeError(f"Could not securely persist secret: {e}")

def get_secret(key: str) -> Optional[str]:
    """Retrieve decrypted secret from the OS credential vault."""
    try:
        return keyring.get_password(VAULT_SERVICE, key)
    except Exception as e:
        logger.error(f"Failed to retrieve secret '{key}' from keyring vault: {e}")
        return None

def delete_secret(key: str) -> bool:
    """Delete secret from the OS credential vault."""
    try:
        keyring.delete_password(VAULT_SERVICE, key)
        return True
    except Exception:
        # Ignore if secret does not exist
        return False

def mask_secret(value: Optional[str]) -> str:
    """Mask secret for GET responses. Returns only indicator or last 4 characters."""
    if not value or not value.strip():
        return ""
    clean = value.strip()
    if len(clean) <= 4:
        return "••••"
    return "••••••••" + clean[-4:]

def save_tokens(platform: str, token_data: dict[str, Any]) -> None:
    """Save serialized OAuth tokens securely in vault."""
    payload = json.dumps(token_data)
    save_secret(f"{platform}_tokens", payload)

def get_tokens(platform: str) -> Optional[dict[str, Any]]:
    """Retrieve and deserialize OAuth tokens from vault."""
    raw = get_secret(f"{platform}_tokens")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception as e:
        logger.error(f"Failed to deserialize tokens for {platform}: {e}")
        return None

def clear_tokens(platform: str) -> None:
    """Delete OAuth tokens for platform."""
    delete_secret(f"{platform}_tokens")
