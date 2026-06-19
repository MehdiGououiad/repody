from __future__ import annotations

NUEXTRACT_TEMPLATE_TYPES = {
    "integer",
    "number",
    "string",
    "verbatim-string",
    "date",
    "time",
    "date-time",
    "duration",
    "boolean",
    "country",
    "currency",
    "language",
    "language-tag",
    "script",
    "url",
    "email-address",
    "phone-number",
    "iban",
    "bic",
    "unit-code",
    "region:US",
    "region:FR",
    "region:IE",
    "region:GB",
    "region:IT",
    "region:ES",
    "region:DE",
    "region:PT",
    "region:CA",
    "region:MX",
    "region:BR",
    "region:AU",
    "region:JP",
    "region:KR",
}

DEFAULT_NUEXTRACT_TEMPLATE_TYPE = "verbatim-string"


def normalize_template_type(value: str | None) -> str:
    raw = (value or "").strip()
    if raw in NUEXTRACT_TEMPLATE_TYPES:
        return raw
    return DEFAULT_NUEXTRACT_TEMPLATE_TYPE
