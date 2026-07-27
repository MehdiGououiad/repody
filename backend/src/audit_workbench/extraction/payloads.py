"""Prompts and response mapping for Repody VLM."""

from __future__ import annotations

import json
from typing import Any

from audit_workbench.catalog.registry import DocumentModelSpec
from audit_workbench.extraction.nuextract import (
    NUEXTRACT_ENABLE_THINKING,
    NUEXTRACT_MARKDOWN_TEMPERATURE,
    NUEXTRACT_STRUCTURED_TEMPERATURE,
    build_vlm_template,
    is_object_array_template_type,
    is_object_template_type,
)
from audit_workbench.extraction.schema import is_nested_object_group
from audit_workbench.extraction.template_types import resolve_template_type
from audit_workbench.extraction.types import ExtractionIclExample, SchemaFieldSpec

def build_vlm_instructions(
    schema: list[SchemaFieldSpec],
    *,
    document_instructions: str = "",
) -> str:
    """NuExtract instructions from per-document notes and field descriptions.

    NuExtract3 puts optional format/location guidance in ``instructions``, not in
    field names. We only forward workflow document notes and per-field descriptions.
    """
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
        if is_object_template_type(resolved) or is_object_array_template_type(resolved):
            for child in field.children or []:
                child_name = child.name.strip()
                if not child_name:
                    continue
                child_desc = (child.description or "").strip()
                if child_desc:
                    path = (
                        f"{name}[].{child_name}"
                        if is_object_array_template_type(resolved)
                        else f"{name}.{child_name}"
                    )
                    field_lines.append(f"- `{path}`: {child_desc}")
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

def _dump_nuextract_template(template: Any) -> str:
    """Serialize template like NuExtract3 multimodal examples (indent=4)."""
    return json.dumps(template, ensure_ascii=False, indent=4)

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

def _serialize_field_value(value: Any) -> str | None:
    """Serialize NuExtract output leaves. Official missing values are null → None here."""
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)

def _append_schema_rows(
    rows: list[dict[str, Any]],
    field: SchemaFieldSpec,
    value: Any,
    *,
    prefix: str = "",
) -> None:
    """Map NuExtract JSON onto schema leaves.

    Nested ``object`` groups expand to dotted keys (``parent.child``).
    ``object-array`` stays one serialized JSON leaf for table rules.
    """
    name = field.name.strip()
    if not name:
        return
    key = f"{prefix}.{name}" if prefix else name
    if is_nested_object_group(field):
        nested: Any = value
        if isinstance(nested, str):
            try:
                nested = json.loads(nested)
            except json.JSONDecodeError:
                nested = {}
        if not isinstance(nested, dict):
            nested = {}
        for child in field.children or []:
            _append_schema_rows(rows, child, nested.get(child.name), prefix=key)
        return
    rows.append({"name": key, "value": _serialize_field_value(value)})

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
        if not field.name.strip():
            continue
        value = payload.get(field.name) if field.name in payload else None
        _append_schema_rows(rows, field, value)
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
        "temperature": NUEXTRACT_STRUCTURED_TEMPERATURE,
        "messages": messages,
        "chat_template_kwargs": {
            "template": _dump_nuextract_template(template),
            "enable_thinking": NUEXTRACT_ENABLE_THINKING,
        },
    }
    if instructions:
        payload["chat_template_kwargs"]["instructions"] = instructions
    return payload

def _markdown_payload(
    *,
    spec: DocumentModelSpec,
    content: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "model": spec.runtime_model,
        "temperature": NUEXTRACT_MARKDOWN_TEMPERATURE,
        "messages": [{"role": "user", "content": content}],
        "chat_template_kwargs": {
            "mode": "markdown",
            "enable_thinking": NUEXTRACT_ENABLE_THINKING,
        },
    }
