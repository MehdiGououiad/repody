"""Identifier helpers."""

import uuid


def new_id(prefix: str) -> str:
    """Return a time-ordered prefixed UUIDv7 identifier (e.g. ``case-019a...``)."""
    return f"{prefix}-{uuid.uuid7().hex}"
