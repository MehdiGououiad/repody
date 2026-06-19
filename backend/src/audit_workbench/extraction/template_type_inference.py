"""NuExtract template type inference — single source of truth for API and extraction."""

from __future__ import annotations

import re

from audit_workbench.extraction.nuextract_types import (
    DEFAULT_NUEXTRACT_TEMPLATE_TYPE,
    normalize_template_type,
)

_EMAIL = re.compile(r"\b(email|e-mail|courriel|mail)\b", re.I)
_PHONE = re.compile(r"\b(phone|tel|mobile|téléphone|telephone|fax)\b", re.I)
_URL = re.compile(r"\b(url|website|lien|link|http)\b", re.I)
_IBAN = re.compile(r"\biban\b", re.I)
_BIC = re.compile(r"\b(bic|swift)\b", re.I)
_COUNTRY = re.compile(r"\b(country|pays|nation)\b", re.I)
_CURRENCY = re.compile(r"\b(currency|devise)\b", re.I)
_AMOUNT = re.compile(r"\b(amount|price|cost|total|fee|montant|balance|prix|tarif)\b", re.I)
_INTEGER = re.compile(r"\b(qty|quantity|quantité|quantite|count|nombre)\b", re.I)
_DATETIME = re.compile(r"\b(date[-_]?time|datetime|horodatage)\b", re.I)
_TIME = re.compile(r"\b(time|heure|hour)\b", re.I)
_DATE = re.compile(r"\b(date|datum|jour)\b", re.I)
_DURATION = re.compile(r"\b(duration|durée|duree)\b", re.I)
_LANGUAGE = re.compile(r"\b(language|langue|lang)\b", re.I)
_PERCENT = re.compile(r"\b(percent|rate|taux|pourcent)\b", re.I)
_BOOLEAN = re.compile(
    r"\b(is_|has_|enabled|active|boolean|true|false|yes|no|oui|non)\b", re.I
)
_VERBATIM = re.compile(
    r"\b(number|numéro|numero|id|ref|reference|invoice|facture|order|commande|sku|code)\b",
    re.I,
)


def _hint_blob(name: str, description: str = "") -> str:
    return f"{name} {description}".replace("_", " ").lower()


def suggest_template_type(name: str, description: str = "") -> str:
    """Infer a NuExtract leaf type from field name and extraction intent."""
    blob = _hint_blob(name, description)
    if _EMAIL.search(blob):
        return "email-address"
    if _PHONE.search(blob):
        return "phone-number"
    if _URL.search(blob):
        return "url"
    if _IBAN.search(blob):
        return "iban"
    if _BIC.search(blob):
        return "bic"
    if _COUNTRY.search(blob):
        return "country"
    if _CURRENCY.search(blob):
        return "currency"
    if _AMOUNT.search(blob):
        return "number"
    if _INTEGER.search(blob):
        return "integer"
    if _DATETIME.search(blob):
        return "date-time"
    if _TIME.search(blob):
        return "time"
    if _DATE.search(blob):
        return "date"
    if _DURATION.search(blob):
        return "duration"
    if _LANGUAGE.search(blob):
        return "language"
    if _PERCENT.search(blob) or "%" in blob:
        return "number"
    if _BOOLEAN.search(blob):
        return "boolean"
    if _VERBATIM.search(blob):
        return "verbatim-string"
    return DEFAULT_NUEXTRACT_TEMPLATE_TYPE


def resolve_template_type(field_name: str, description: str = "", template_type: str | None = None) -> str:
    """Use explicit template type when set, otherwise infer."""
    explicit = (template_type or "").strip()
    if explicit:
        return normalize_template_type(explicit)
    return suggest_template_type(field_name, description)


def vlm_max_tokens_for_field_count(
    field_count: int,
    *,
    ceiling: int = 4096,
    enable_thinking: bool = False,
) -> int:
    """Scale completion budget with schema size: min(4096, 128 + 48 × fields)."""
    base = min(ceiling, max(128, 128 + 48 * max(field_count, 0)))
    if enable_thinking:
        # NuExtract reasoning can consume most of the budget before JSON output.
        return min(ceiling, max(base, 1024))
    return base


def vlm_max_tokens_for_markdown(
    *,
    page_count: int = 1,
    ceiling: int = 8192,
    enable_thinking: bool = False,
) -> int:
    """Scale markdown budget with page count for NuExtract document-to-Markdown."""
    base = min(ceiling, max(1024, 768 + 640 * max(page_count, 1)))
    if enable_thinking:
        return min(ceiling, max(base, 2048))
    return base
