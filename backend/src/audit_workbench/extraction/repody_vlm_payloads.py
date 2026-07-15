from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from audit_workbench.extraction.base import ExtractionIclExample, SchemaFieldSpec
from audit_workbench.extraction.nuextract_contract import NUEXTRACT_ENABLE_THINKING
from audit_workbench.extraction.nuextract_template import build_vlm_template
from audit_workbench.extraction.nuextract_types import is_object_array_template_type
from audit_workbench.extraction.template_type_inference import resolve_template_type

if TYPE_CHECKING:
    from audit_workbench.catalog.registry import DocumentModelSpec


def build_vlm_instructions(
    schema: list[SchemaFieldSpec],
    *,
    document_instructions: str = "",
) -> str:
    """NuExtract instructions from per-document notes and field descriptions."""
    lines: list[str] = []
    doc_block = (document_instructions or "").strip()
    if doc_block:
        lines.append(doc_block)
    field_lines: list[str] = []
    for field in schema:
        name = field.name.strip()
        if not name:
            continue
        description = (field.description or "").strip()
        resolved = resolve_template_type(name, field.description, field.template_type)
        if description:
            field_lines.append(f"- `{name}`: {description}")
        if is_object_array_template_type(resolved):
            for child in field.children or []:
                child_name = child.name.strip()
                if not child_name:
                    continue
                child_desc = (child.description or "").strip()
                if child_desc:
                    field_lines.append(f"- `{name}[].{child_name}`: {child_desc}")
    if field_lines:
        lines.append("Field instructions:")
        lines.extend(field_lines)
    return "\n".join(lines)


def build_icl_messages(examples: list[ExtractionIclExample]) -> list[dict[str, Any]]:
    """NuExtract in-context examples via developer-role message pairs."""
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


def _apply_vlm_generation_kwargs(payload: dict[str, Any]) -> None:
    payload["temperature"] = 0.2


_THINKING_END_TAGS = (
    "</think>",
    "</" + "think" + ">",
)


def strip_vlm_thinking(raw: str) -> str:
    """Drop NuExtract reasoning wrapper when thinking mode is enabled."""
    for tag in _THINKING_END_TAGS:
        if tag in raw:
            return raw.split(tag, 1)[1].strip()
    return raw.strip()


def _serialize_field_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _fields_payload(raw: str, schema: list[SchemaFieldSpec]) -> str:
    try:
        payload = json.loads(raw.strip())
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        try:
            payload = json.loads(raw[start : end + 1]) if start >= 0 and end > start else {}
        except json.JSONDecodeError:
            payload = {}
    if not isinstance(payload, dict):
        payload = {}

    rows: list[dict[str, Any]] = []
    for field in schema:
        value = payload.get(field.name)
        rows.append(
            {
                "name": field.name,
                "value": _serialize_field_value(value),
            }
        )
    return json.dumps({"fields": rows}, ensure_ascii=False)


def _structured_payload(
    *,
    spec: DocumentModelSpec,
    content: list[dict[str, Any]],
    schema: list[SchemaFieldSpec],
    extraction_instructions: str,
    extraction_icl_examples: list[ExtractionIclExample] | None = None,
) -> dict[str, Any]:
    template = build_vlm_template(schema)
    instructions = build_vlm_instructions(
        schema,
        document_instructions=extraction_instructions,
    )
    messages = [
        *build_icl_messages(extraction_icl_examples or []),
        {"role": "user", "content": content},
    ]
    payload: dict[str, Any] = {
        "model": spec.runtime_model,
        "messages": messages,
        "chat_template_kwargs": {
            "template": json.dumps(template, ensure_ascii=False, separators=(",", ":")),
            "enable_thinking": NUEXTRACT_ENABLE_THINKING,
        },
    }
    _apply_vlm_generation_kwargs(payload)
    if instructions:
        payload["chat_template_kwargs"]["instructions"] = instructions
    return payload


def _markdown_payload(
    *,
    spec: DocumentModelSpec,
    content: list[dict[str, Any]],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": spec.runtime_model,
        "messages": [{"role": "user", "content": content}],
        "chat_template_kwargs": {
            "mode": "markdown",
            "enable_thinking": NUEXTRACT_ENABLE_THINKING,
        },
    }
    _apply_vlm_generation_kwargs(payload)
    return payload
