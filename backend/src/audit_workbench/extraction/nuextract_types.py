from __future__ import annotations

_LIST_SUFFIX = "-list"

NUEXTRACT_SCALAR_TEMPLATE_TYPES = {
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

NUEXTRACT_LIST_TEMPLATE_TYPES = {
    f"{scalar}{_LIST_SUFFIX}" for scalar in NUEXTRACT_SCALAR_TEMPLATE_TYPES
}

NUEXTRACT_STRUCTURE_TEMPLATE_TYPES = {
    "enum",
    "multi-enum",
    "object-array",
}

NUEXTRACT_TEMPLATE_TYPES = (
    NUEXTRACT_SCALAR_TEMPLATE_TYPES
    | NUEXTRACT_LIST_TEMPLATE_TYPES
    | NUEXTRACT_STRUCTURE_TEMPLATE_TYPES
)

DEFAULT_NUEXTRACT_TEMPLATE_TYPE = "verbatim-string"


def is_list_template_type(value: str | None) -> bool:
    raw = (value or "").strip()
    if not raw.endswith(_LIST_SUFFIX) or is_structure_template_type(raw):
        return False
    scalar = raw[: -len(_LIST_SUFFIX)]
    return scalar in NUEXTRACT_SCALAR_TEMPLATE_TYPES


def is_enum_template_type(value: str | None) -> bool:
    return (value or "").strip() == "enum"


def is_multi_enum_template_type(value: str | None) -> bool:
    return (value or "").strip() == "multi-enum"


def is_object_array_template_type(value: str | None) -> bool:
    return (value or "").strip() == "object-array"


def is_structure_template_type(value: str | None) -> bool:
    raw = (value or "").strip()
    return raw in NUEXTRACT_STRUCTURE_TEMPLATE_TYPES


def list_template_scalar_type(value: str) -> str:
    """Map `number-list` → `number` for NuExtract array leaf types."""
    if not is_list_template_type(value):
        return value
    return value[: -len(_LIST_SUFFIX)]


def template_type_to_nuextract_leaf(value: str) -> str:
    """NuExtract3 scalar leaf type string."""
    normalized = normalize_template_type(value)
    if is_structure_template_type(normalized) or is_list_template_type(normalized):
        raise ValueError(f"Use build_field_template_node for structure type {normalized!r}")
    return normalized


def normalize_template_type(value: str | None) -> str:
    raw = (value or "").strip()
    if raw in NUEXTRACT_SCALAR_TEMPLATE_TYPES or raw in NUEXTRACT_STRUCTURE_TEMPLATE_TYPES:
        return raw
    if is_list_template_type(raw):
        return raw
    return DEFAULT_NUEXTRACT_TEMPLATE_TYPE
