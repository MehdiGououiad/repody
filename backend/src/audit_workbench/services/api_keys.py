"""Workflow API key hashing and verification."""

from __future__ import annotations

import hashlib
import secrets


def hash_api_key(raw_key: str) -> str:
    """Return a hex SHA-256 digest suitable for persistence."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def verify_api_key(provided: str | None, stored_hash: str | None) -> bool:
    """Constant-time compare of a plaintext key against a stored hash."""
    if not provided or not stored_hash:
        return False
    return secrets.compare_digest(hash_api_key(provided), stored_hash)


def api_key_hint(raw_key: str) -> str:
    """Masked hint for UI display (never log or persist the full key)."""
    prefix = raw_key[:12] if len(raw_key) >= 12 else raw_key
    return f"{prefix}********"


def is_stored_hash(value: str | None) -> bool:
    """True when value looks like a SHA-256 hex digest."""
    if not value or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True
