"""NuExtract3 types, templates, and chat.completions payloads.

Docs:
  https://huggingface.co/numind/NuExtract3-GGUF
  https://github.com/numindai/nuextract
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from repody.extraction.types import DEFAULT_TEMPLATE_TYPE, ExtractionIclExample, SchemaFieldSpec
from repody.settings import get_settings

# https://huggingface.co/numind/NuExtract3-GGUF
# https://github.com/numindai/nuextract - non-thinking / markdown examples
NUEXTRACT_PDF_DPI = 170
NUEXTRACT_STRUCTURED_TEMPERATURE = 0.2
NUEXTRACT_MARKDOWN_TEMPERATURE = 0.0
NUEXTRACT_THINKING_TEMPERATURE = 0.6
# Official reasoning (markdown + thinking) example uses 0.7.
NUEXTRACT_MARKDOWN_THINKING_TEMPERATURE = 0.7
# Heading for per-field notes inside the official free-text `instructions`.
NUEXTRACT_FIELD_NOTES_HEADING = "Field guidance:"


# Platform encoding of an official list type: `number-list` stands for `["number"]`.
LIST_SUFFIX = "-list"


def normalize_template_type(value: str | None) -> str:
    """Official TYPES.md leaf name, structure type or `<leaf>-list`; unknown leaves pass through."""
    return (value or "").strip() or DEFAULT_TEMPLATE_TYPE


def is_list_template_type(value: str | None) -> bool:
    raw = normalize_template_type(value)
    return raw.endswith(LIST_SUFFIX) and len(raw) > len(LIST_SUFFIX)


def _choices(field: SchemaFieldSpec) -> list[str]:
    """Official enum / multi-enum need at least two choices."""
    values = field.enum_values or []
    if len(values) < 2:
        raise ValueError(
            f"{field.template_type} field {field.name!r} requires at least 2 choices "
            f"(got {len(values)})"
        )
    return values


def build_field_template_node(field: SchemaFieldSpec) -> Any:
    """Official NuExtract template node for one schema field (recursive)."""
    template_type = field.template_type
    match template_type:
        case "object" | "object-array":
            row = {child.name: build_field_template_node(child) for child in field.children or []}
            # Official empty object is {}; an object-array prototype is a one-element list.
            return [row] if template_type == "object-array" else row
        case "multi-enum":
            return [_choices(field)]
        case "enum":
            return _choices(field)
        case _ if is_list_template_type(template_type):
            return [template_type.removesuffix(LIST_SUFFIX)]
        case _:
            return template_type


def build_nuextract_template(schema: list[SchemaFieldSpec]) -> dict[str, Any]:
    """Official NuExtract JSON template object from schema fields."""
    return {field.name: build_field_template_node(field) for field in schema if field.name}


# --- Chat completions (official NuExtract multimodal / markdown) ---


def _iter_field_notes(fields: list[SchemaFieldSpec], prefix: str = "") -> Iterator[tuple[str, str]]:
    """Yield ``(dotted_path, description)`` for every described field, depth-first."""
    for field in fields:
        name = field.name.strip()
        if not name:
            continue
        path = f"{prefix}{name}"
        description = (field.description or "").strip()
        if description:
            yield path, description
        children = field.children or []
        if children:
            yield from _iter_field_notes(children, f"{path}.")


def build_nuextract_instructions(
    schema: list[SchemaFieldSpec],
    *,
    document_instructions: str = "",
) -> str:
    """Official free-text ``instructions``: document notes plus per-field guidance.

    NuExtract3 keeps hints out of the template and in ``instructions``, so schema
    field descriptions are rendered here rather than encoded into field names.
    """
    blocks: list[str] = []
    document_notes = (document_instructions or "").strip()
    if document_notes:
        blocks.append(document_notes)
    field_notes = [f"- {path}: {text}" for path, text in _iter_field_notes(schema)]
    if field_notes:
        blocks.append("\n".join([NUEXTRACT_FIELD_NOTES_HEADING, *field_notes]))
    return "\n\n".join(blocks)


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


_THINKING_END_TAG = "</think>"


def strip_thinking(raw: str) -> str:
    """Drop NuExtract reasoning wrapper when thinking mode is enabled."""
    if _THINKING_END_TAG in raw:
        return raw.split(_THINKING_END_TAG, 1)[1].strip()
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
        NUEXTRACT_THINKING_TEMPERATURE if enable_thinking else NUEXTRACT_STRUCTURED_TEMPERATURE
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
    enable_thinking = bool(settings.repody_vlm_enable_thinking)
    temperature = (
        NUEXTRACT_MARKDOWN_THINKING_TEMPERATURE
        if enable_thinking
        else NUEXTRACT_MARKDOWN_TEMPERATURE
    )
    return {
        "model": model,
        "temperature": temperature,
        "messages": [{"role": "user", "content": content}],
        "chat_template_kwargs": {
            "mode": "markdown",
            "enable_thinking": enable_thinking,
        },
    }
