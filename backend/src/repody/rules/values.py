"""Extracted text as rules see it: field keys, amounts, dates and the missing marker."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from price_parser import Price

# Stored for a schema field the model did not extract; rules treat it as absent.
MISSING = "—"

_ISO_DATE_OR_TIME = re.compile(
    r"^(\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?.*)?|\d{2}:\d{2}(:\d{2})?)$"
)
_FIRST_DIGIT = re.compile(r"\d")
_LETTER = re.compile(r"[A-Za-z]")


def field_key(name: str) -> str:
    """Canonical name of a field: ``Total Amount`` -> ``total_amount``, ``a.b`` -> ``a__b``."""
    return name.strip().lower().replace(" ", "_").replace(".", "__")


def is_iso_date_like(text: str) -> bool:
    """ISO date, datetime or time text (compared as strings, never parsed as amounts)."""
    return bool(_ISO_DATE_OR_TIME.match((text or "").strip()))


def _amount(value: str) -> Decimal | None:
    """Signed amount from ``6 000,00 Dh``, ``1.234,56`` or ``-50.00 MAD`` via price-parser.

    Text with letters before the first digit (``PO-2024-991``) is an identifier, not an
    amount. price-parser drops the sign, so a leading ``-`` is reapplied.
    """
    text = value.strip().replace("−", "-")  # noqa: RUF001 (Unicode minus sign)
    if not text or text == MISSING or is_iso_date_like(text):
        return None
    first_digit = _FIRST_DIGIT.search(text)
    if first_digit is None or _LETTER.search(text[: first_digit.start()]):
        return None
    amount = Price.fromstring(text).amount
    if amount is None:
        return None
    return -amount if "-" in text[: first_digit.start()] else amount


def normalize_amount(value: str) -> str:
    """Canonical decimal string (``6 000,00`` -> ``6000.00``); other text unchanged."""
    amount = _amount(value)
    return str(amount) if amount is not None else value.strip()


def parse_numeric_value(value: str) -> float | None:
    """Numeric value of a text, ignoring currency labels; None for identifiers and dates."""
    amount = _amount(value)
    return float(amount) if amount is not None else None


def coerce(raw: str | None) -> Any:
    """None when missing; ISO date text as is; then a number, a bool, or the text."""
    text = (raw or "").strip()
    if not text or text == MISSING:
        return None
    if is_iso_date_like(text):
        return text
    number = parse_numeric_value(text)
    if number is not None:
        return number
    if text.lower() in ("true", "false"):
        return text.lower() == "true"
    return text
