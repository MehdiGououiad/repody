"""Shared text helpers for OCR and suite scoring."""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation


def digits_only(value: object) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def normalize_space(value: object) -> str:
    folded = unicodedata.normalize("NFKC", str(value or ""))
    return " ".join(folded.casefold().split())


def parse_amount(value: object) -> Decimal | None:
    raw = unicodedata.normalize("NFKC", str(value or "")).strip()
    if not raw:
        return None
    cleaned = re.sub(r"[^\d,.\-]", "", raw)
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        tail = cleaned.rsplit(",", 1)[-1]
        cleaned = cleaned.replace(",", ".") if len(tail) <= 2 else cleaned.replace(",", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None
