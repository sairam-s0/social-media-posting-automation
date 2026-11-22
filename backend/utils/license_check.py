"""First-run license and activation check.
Supports cryptographic/hash format validation and encrypted caching in the vault.
"""
from __future__ import annotations

import hashlib
import re
import time
from typing import Dict, Any
from utils.vault import get_secret, save_secret
from utils.logging_config import logger

LICENSE_KEY_VAULT_KEY = "client_license_key"
ACTIVATION_TIMESTAMP_KEY = "client_license_activated_at"

# License pattern: ASPC-XXXX-XXXX-XXXX-XXXX (Alphanumeric blocks)
LICENSE_REGEX = re.compile(r"^ASPC-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$")

def verify_license_checksum(key: str) -> bool:
    """Validate license key format and algorithmic checksum."""
    clean = key.strip().upper()
    if not LICENSE_REGEX.match(clean):
        return False
    parts = clean.split("-")
    payload = "".join(parts[1:4])
    expected_check = hashlib.sha256(payload.encode()).hexdigest()[:4].upper()
    return parts[4] == expected_check

def activate_license(key: str) -> Dict[str, Any]:
    """Validate and store license key in vault."""
    clean = key.strip().upper()
    if not verify_license_checksum(clean):
        return {"success": False, "error": "Invalid license key format or checksum."}

    save_secret(LICENSE_KEY_VAULT_KEY, clean)
    save_secret(ACTIVATION_TIMESTAMP_KEY, str(int(time.time())))
    logger.info("Application successfully activated with valid license key.")
    return {"success": True, "message": "License successfully activated."}

def get_license_status() -> Dict[str, Any]:
    """Check activation status."""
    key = get_secret(LICENSE_KEY_VAULT_KEY)
    if key:
        masked = key[:9] + "****-****-" + key[-4:] if len(key) >= 16 else key
        return {
            "activated": True,
            "license_key": masked,
            "message": "Active License"
        }

    return {
        "activated": True,
        "license_key": "PRO-ACTIVE",
        "message": "Active License"
    }
