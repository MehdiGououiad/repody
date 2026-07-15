"""NuExtract template type inference — single source of truth for API and extraction."""

from __future__ import annotations

import re

from audit_workbench.extraction.nuextract_types import DEFAULT_NUEXTRACT_TEMPLATE_TYPE, normalize_template_type

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
_LIST = re.compile(
    r"\b(liste|list|each|every|tous les|all|multiple)\b",
    re.I,
)


def _hint_blob(name: str, description: str = "") -> str:
    return f"{name} {description}".replace("_", " ").lower()


def _with_list_suffix(leaf: str) -> str:
    return f"{leaf}-list"


def suggest_template_type(name: str, description: str = "") -> str:
    """Infer a NuExtract leaf type from field name and extraction intent."""
    blob = _hint_blob(name, description)
    wants_list = bool(_LIST.search(blob))
    if _EMAIL.search(blob):
        return _with_list_suffix("email-address") if wants_list else "email-address"
    if _PHONE.search(blob):
        return _with_list_suffix("phone-number") if wants_list else "phone-number"
    if _URL.search(blob):
        return _with_list_suffix("url") if wants_list else "url"
    if _IBAN.search(blob):
        return _with_list_suffix("iban") if wants_list else "iban"
    if _BIC.search(blob):
        return _with_list_suffix("bic") if wants_list else "bic"
    if _COUNTRY.search(blob):
        return _with_list_suffix("country") if wants_list else "country"
    if _CURRENCY.search(blob):
        return _with_list_suffix("currency") if wants_list else "currency"
    if _AMOUNT.search(blob):
        return _with_list_suffix("number") if wants_list else "number"
    if _INTEGER.search(blob):
        return _with_list_suffix("integer") if wants_list else "integer"
    if _DATETIME.search(blob):
        return _with_list_suffix("date-time") if wants_list else "date-time"
    if _TIME.search(blob):
        return _with_list_suffix("time") if wants_list else "time"
    if _DATE.search(blob):
        return _with_list_suffix("date") if wants_list else "date"
    if _DURATION.search(blob):
        return _with_list_suffix("duration") if wants_list else "duration"
    if _LANGUAGE.search(blob):
        return _with_list_suffix("language") if wants_list else "language"
    if _PERCENT.search(blob) or "%" in blob:
        return "number"
    if _BOOLEAN.search(blob):
        return _with_list_suffix("boolean") if wants_list else "boolean"
    if _VERBATIM.search(blob):
        return _with_list_suffix("verbatim-string") if wants_list else "verbatim-string"
    return _with_list_suffix(DEFAULT_NUEXTRACT_TEMPLATE_TYPE) if wants_list else DEFAULT_NUEXTRACT_TEMPLATE_TYPE


def resolve_template_type(field_name: str, description: str = "", template_type: str | None = None) -> str:
    """Use explicit template type when set, otherwise infer."""
    explicit = (template_type or "").strip()
    if explicit:
        return normalize_template_type(explicit)
    return suggest_template_type(field_name, description)
