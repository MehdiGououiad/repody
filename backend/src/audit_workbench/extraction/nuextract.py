"""NuExtract3 types, constants, and JSON template builders."""

from __future__ import annotations

from typing import Any

from audit_workbench.extraction.types import SchemaFieldSpec
from audit_workbench.settings import Settings

# https://huggingface.co/numind/NuExtract3-GGUF
# https://github.com/numindai/nuextract — non-thinking / markdown examples
NUEXTRACT_PDF_DPI = 170
NUEXTRACT_ENABLE_THINKING = False
NUEXTRACT_MAX_PAGES_PER_REQUEST = 6
NUEXTRACT_STRUCTURED_TEMPERATURE = 0.2
NUEXTRACT_MARKDOWN_TEMPERATURE = 0.0


def extraction_inference_profile_key(*, settings: Settings) -> str:
    served_model = (settings.llamacpp_served_model or "").strip().lower()
    return f"nuextract:official:model:{served_model or 'default'}"


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
    "object",
    "object-array",
}

NUEXTRACT_TEMPLATE_TYPES = (
    NUEXTRACT_SCALAR_TEMPLATE_TYPES
    | NUEXTRACT_LIST_TEMPLATE_TYPES
    | NUEXTRACT_STRUCTURE_TEMPLATE_TYPES
)

DEFAULT_NUEXTRACT_TEMPLATE_TYPE = "verbatim-string"

# HF prose sometimes uses short aliases; TYPES.md is the source of truth.
NUEXTRACT_TYPE_ALIASES = {
    "email": "email-address",
    "phone": "phone-number",
    "tel": "phone-number",
}


def canonical_nuextract_leaf_type(value: str | None) -> str:
    """Map a leaf type string to the TYPES.md form (pass through unknowns)."""
    raw = (value or "").strip()
    if not raw:
        return DEFAULT_NUEXTRACT_TEMPLATE_TYPE
    return NUEXTRACT_TYPE_ALIASES.get(raw, raw)


def is_list_template_type(value: str | None) -> bool:
    raw = (value or "").strip()
    if not raw.endswith(_LIST_SUFFIX) or is_structure_template_type(raw):
        return False
    # Platform encoding of official ["type"] arrays — allow catalogued and passthrough scalars.
    return bool(raw[: -len(_LIST_SUFFIX)])


def is_enum_template_type(value: str | None) -> bool:
    return (value or "").strip() == "enum"


def is_multi_enum_template_type(value: str | None) -> bool:
    return (value or "").strip() == "multi-enum"


def is_object_array_template_type(value: str | None) -> bool:
    return (value or "").strip() == "object-array"


def is_object_template_type(value: str | None) -> bool:
    return (value or "").strip() == "object"


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
    """Normalize platform template types; pass through unknown official leaf strings."""
    raw = canonical_nuextract_leaf_type(value)
    if raw in NUEXTRACT_STRUCTURE_TEMPLATE_TYPES:
        return raw
    if raw in NUEXTRACT_SCALAR_TEMPLATE_TYPES:
        return raw
    if is_list_template_type(raw):
        scalar = raw[: -len(_LIST_SUFFIX)]
        canonical_scalar = canonical_nuextract_leaf_type(scalar)
        if canonical_scalar != scalar:
            return f"{canonical_scalar}{_LIST_SUFFIX}"
        return raw
    # Keep unknown leaf type strings (official templates may introduce new types).
    return raw


def build_field_template_node(field: SchemaFieldSpec) -> Any:
    """Recursive NuExtract template node for one schema field."""
    # Deferred: template_types imports normalize_template_type from this module.
    from audit_workbench.extraction.template_types import resolve_template_type

    resolved = resolve_template_type(field.name, field.description, field.template_type)
    children = [c for c in (field.children or []) if c.name.strip()]
    # Nested children without object-array → official object group `{}`.
    as_object = is_object_template_type(resolved) or (
        bool(children) and not is_object_array_template_type(resolved)
    )

    if as_object or is_object_array_template_type(resolved):
        row: dict[str, Any] = {}
        for child in children:
            row[child.name.strip()] = build_field_template_node(child)
        # Official empty object is {}; object-array prototype is a one-element list.
        if is_object_array_template_type(resolved):
            return [row]
        return row

    if is_multi_enum_template_type(resolved):
        values = _clean_enum_values(field.enum_values)
        # Official multi-enum: [["A", "B", ...]] with ≥2 choices — never invent placeholders.
        if len(values) >= 2:
            return [values]
        return ["verbatim-string"]

    if is_enum_template_type(resolved):
        values = _clean_enum_values(field.enum_values)
        # Official enum: ["a", "b", ...] with ≥2 choices — never invent "other".
        if len(values) >= 2:
            return values
        return "verbatim-string"

    if is_list_template_type(resolved):
        return [list_template_scalar_type(resolved)]

    return template_type_to_nuextract_leaf(resolved)


def build_vlm_template(schema: list[SchemaFieldSpec]) -> dict[str, Any]:
    template: dict[str, Any] = {}
    for field in schema:
        name = field.name.strip()
        if not name:
            continue
        template[name] = build_field_template_node(field)
    return template


def _clean_enum_values(values: list[str] | None) -> list[str]:
    if not values:
        return []
    seen: set[str] = set()
    cleaned: list[str] = []
    for raw in values:
        token = raw.strip()
        if not token or token in seen:
            continue
        seen.add(token)
        cleaned.append(token)
    return cleaned
