"""Amount parsing for rule comparisons, via price-parser (not extraction storage)."""

from __future__ import annotations

import re
from decimal import Decimal

from price_parser import Price

from repody.rules.value_coercion import MISSING, is_iso_date_like

_FIRST_DIGIT = re.compile(r"\d")


def _amount(value: str) -> Decimal | None:
    """Signed amount from text like ``6 000,00 Dh``, ``1.234,56`` or ``-50.00 MAD``.

    Text with letters before the first digit is an identifier (``PO-2024-991``,
    ``FAC-42``), not an amount. price-parser handles separators and currency
    labels but drops the sign, so a leading ``-`` is applied here.
    """
    s = value.strip().replace("\u2212", "-")
    if not s or s == MISSING or is_iso_date_like(s):
        return None
    first_digit = _FIRST_DIGIT.search(s)
    if first_digit is None:
        return None
    prefix = s[: first_digit.start()]
    if re.search(r"[A-Za-z]", prefix):
        return None
    amount = Price.fromstring(s).amount
    if amount is None:
        return None
    return -amount if "-" in prefix else amount


def normalize_amount(value: str) -> str:
    """Canonical decimal string (``6 000,00`` -> ``6000.00``); unparsable text is returned as-is."""
    amount = _amount(value)
    return str(amount) if amount is not None else value.strip()


def parse_numeric_value(value: str) -> float | None:
    """Numeric value of a field, ignoring currency labels; None for identifiers and dates."""
    amount = _amount(value)
    return float(amount) if amount is not None else None
