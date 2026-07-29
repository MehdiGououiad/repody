"""NuExtract3 types, templates, and chat.completions payloads.

Docs:
  https://huggingface.co/numind/NuExtract3-GGUF
  https://github.com/numindai/nuextract
"""

from __future__ import annotations

import json
from typing import Any

from repody.extraction.types import ExtractionIclExample, SchemaFieldSpec
from repody.settings import Settings, get_settings

# https://huggingface.co/numind/NuExtract3-GGUF
# https://github.com/numindai/nuextract — non-thinking / markdown examples
NUEXTRACT_PDF_DPI = 170
NUEXTRACT_ENABLE_THINKING = False
# Official PDF examples send every page. None = no client-side cap (match docs).
# Set AUDIT_REPODY_VLM_MAX_PAGES_PER_REQUEST to cap for low-memory llama.cpp.
NUEXTRACT_MAX_PAGES_PER_REQUEST: int | None = None
NUEXTRACT_STRUCTURED_TEMPERATURE = 0.2
NUEXTRACT_MARKDOWN_TEMPERATURE = 0.0
NUEXTRACT_THINKING_TEMPERATURE = 0.6


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


def canonical_nuextract_leaf_type(value: str | None) -> str:
    """Pass through official TYPES.md leaf names (no platform aliases)."""
    raw = (value or "").strip()
    if not raw:
        return DEFAULT_NUEXTRACT_TEMPLATE_TYPE
    return raw


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


def suggest_template_type(name: str, description: str = "") -> str:
    """Official default leaf type (no name/description heuristics)."""
    del name, description
    return DEFAULT_NUEXTRACT_TEMPLATE_TYPE


def resolve_template_type(
    field_name: str, description: str = "", template_type: str | None = None
) -> str:
    """Use explicit template type when set, otherwise the NuExtract default."""
    del field_name, description
    explicit = (template_type or "").strip()
    if explicit:
        return normalize_template_type(explicit)
    return DEFAULT_NUEXTRACT_TEMPLATE_TYPE


def build_field_template_node(field: SchemaFieldSpec) -> Any:
    """Recursive NuExtract template node for one schema field."""
    resolved = resolve_template_type(field.name, field.description, field.template_type)
    children = [c for c in (field.children or []) if c.name.strip()]

    if is_object_template_type(resolved) or is_object_array_template_type(resolved):
        row: dict[str, Any] = {}
        for child in children:
            row[child.name.strip()] = build_field_template_node(child)
        # Official empty object is {}; object-array prototype is a one-element list.
        if is_object_array_template_type(resolved):
            return [row]
        return row

    if is_multi_enum_template_type(resolved):
        values = _clean_enum_values(field.enum_values)
        # Official multi-enum: [["A", "B", ...]] with ≥2 choices.
        if len(values) < 2:
            raise ValueError(
                f"multi-enum field {field.name!r} requires at least 2 choices "
                f"(got {len(values)})"
            )
        return [values]

    if is_enum_template_type(resolved):
        values = _clean_enum_values(field.enum_values)
        # Official enum: ["a", "b", ...] with ≥2 choices.
        if len(values) < 2:
            raise ValueError(
                f"enum field {field.name!r} requires at least 2 choices "
                f"(got {len(values)})"
            )
        return values

    if is_list_template_type(resolved):
        return [list_template_scalar_type(resolved)]

    return template_type_to_nuextract_leaf(resolved)


def build_nuextract_template(schema: list[SchemaFieldSpec]) -> dict[str, Any]:
    """Official NuExtract JSON template object from schema fields."""
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


# --- Chat completions (official NuExtract multimodal / markdown) ---

def build_nuextract_instructions(
    schema: list[SchemaFieldSpec],
    *,
    document_instructions: str = "",
) -> str:
    """Official ``instructions`` — workflow document notes only."""
    _ = schema
    return (document_instructions or "").strip()


def build_icl_messages(examples: list[ExtractionIclExample]) -> list[dict[str, Any]]:
    """In-context examples as developer-role message pairs."""
    messages: list[dict[str, Any]] = []
    for example in examples:
        input_text = example.input.strip()
        output_text = example.output.strip()
        if not input_text or not output_text:
            continue
        messages.append(
            {
                "role": "developer",
                "content": [
                    {"type": "text", "text": input_text},
                    {"type": "text", "text": output_text},
                ],
            }
        )
    return messages


def dump_nuextract_template(template: Any) -> str:
    """Serialize template like NuExtract3 multimodal examples (indent=4)."""
    return json.dumps(template, ensure_ascii=False, indent=4)


_THINKING_END_TAGS = ("</think>", "</" + "think" + ">")


def strip_thinking(raw: str) -> str:
    """Drop NuExtract reasoning wrapper when thinking mode is enabled."""
    for tag in _THINKING_END_TAGS:
        if tag in raw:
            return raw.split(tag, 1)[1].strip()
    return raw.strip()


def structured_chat_payload(
    *,
    model: str,
    content: list[dict[str, Any]],
    schema: list[SchemaFieldSpec],
    extraction_instructions: str,
    extraction_icl_examples: list[ExtractionIclExample] | None = None,
) -> dict[str, Any]:
    """Official structured extraction chat.completions body."""
    settings = get_settings()
    enable_thinking = bool(settings.repody_vlm_enable_thinking)
    temperature = (
        NUEXTRACT_THINKING_TEMPERATURE
        if enable_thinking
        else NUEXTRACT_STRUCTURED_TEMPERATURE
    )
    # Official ICL demos use temperature 0 when examples are present.
    if extraction_icl_examples and not enable_thinking:
        temperature = 0.0

    payload: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "messages": [
            *build_icl_messages(extraction_icl_examples or []),
            {"role": "user", "content": content},
        ],
        "chat_template_kwargs": {
            "template": dump_nuextract_template(build_nuextract_template(schema)),
            "enable_thinking": enable_thinking,
        },
    }
    instructions = build_nuextract_instructions(
        schema, document_instructions=extraction_instructions
    )
    if instructions:
        payload["chat_template_kwargs"]["instructions"] = instructions
    return payload


def markdown_chat_payload(
    *,
    model: str,
    content: list[dict[str, Any]],
) -> dict[str, Any]:
    """Official markdown-mode chat.completions body."""
    settings = get_settings()
    return {
        "model": model,
        "temperature": NUEXTRACT_MARKDOWN_TEMPERATURE,
        "messages": [{"role": "user", "content": content}],
        "chat_template_kwargs": {
            "mode": "markdown",
            "enable_thinking": bool(settings.repody_vlm_enable_thinking),
        },
    }
