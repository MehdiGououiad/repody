"""Amount parsing helpers for rules comparison (not extraction storage)."""

from __future__ import annotations

import re

from repody.rules.value_coercion import is_iso_date_like

_NUMERIC_RUN = re.compile(r"[+-]?[\d][\d\s.,]*")


def _locale_normalize_numeric(token: str) -> str:
    s = token.strip().replace("\u00a0", " ").replace(" ", "")
    if not s:
        return s
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            s = f"{parts[0]}.{parts[1]}"
        else:
            s = s.replace(",", ".")
    return s


def normalize_amount(value: str) -> str:
    """Locale amount parse for rules comparison only — not extraction storage."""
    s = value.strip()
    if not s or s == "—":
        return s
    match = _NUMERIC_RUN.search(s.replace("\u00a0", " "))
    if not match:
        return s
    return _locale_normalize_numeric(match.group(0))


def parse_numeric_value(value: str) -> float | None:
    """Parse a numeric field value, ignoring trailing currency labels."""
    s = value.strip()
    if not s or s == "—":
        return None
    if is_iso_date_like(s):
        return None
    match = _NUMERIC_RUN.search(s.replace("\u00a0", " "))
    if not match:
        return None
    start, _end = match.span()
    prefix = s[:start].strip()
    # Reject alphanumeric IDs like PO-2024-991 where digits sit inside a token.
    if prefix and re.search(r"[A-Za-z]", prefix):
        return None
    normalized = normalize_amount(s)
    if not normalized or normalized == "—":
        return None
    try:
        if re.match(r"^-?\d+(\.\d+)?$", normalized):
            return float(normalized)
    except ValueError:
        pass
    return None
