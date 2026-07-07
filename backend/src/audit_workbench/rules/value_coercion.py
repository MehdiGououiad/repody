"""Shared helpers for rule operand typing (dates vs numbers vs strings)."""

from __future__ import annotations

import re

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ISO_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2})?")
_ISO_TIME = re.compile(r"^\d{2}:\d{2}(:\d{2})?$")


def is_iso_date_like(text: str) -> bool:
    """True for ISO dates/times from schema rules or HTML date inputs."""
    value = (text or "").strip()
    if not value:
        return False
    return bool(
        _ISO_DATE.match(value) or _ISO_DATETIME.match(value) or _ISO_TIME.match(value)
    )
