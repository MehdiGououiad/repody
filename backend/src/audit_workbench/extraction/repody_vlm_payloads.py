from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from audit_workbench.extraction.base import SchemaFieldSpec
from audit_workbench.extraction.template_type_inference import (
    resolve_template_type,
    vlm_max_tokens_for_field_count,
    vlm_max_tokens_for_markdown,
)
from audit_workbench.settings import Settings

if TYPE_CHECKING:
    from audit_workbench.catalog.registry import DocumentModelSpec

_MONEY_HINTS = (
    "amount",
    "total",
    "tax",
    "tva",
    "ttc",
    "price",
    "prix",
    "cost",
    "fee",
    "montant",
    "balance",
)


def build_vlm_template(schema: list[SchemaFieldSpec]) -> dict[str, str]:
    template: dict[str, str] = {}
    for field in schema:
        name = field.name.strip()
        if not name:
            continue
        template[name] = resolve_template_type(name, field.description, field.template_type)
    return template


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
        if description:
            field_lines.append(f"- `{name}`: {description}")
    if field_lines:
        lines.append("Field instructions:")
        lines.extend(field_lines)
    return "\n".join(lines)


_NUEXTRACT_THINKING_TOP_P = 0.95
_NUEXTRACT_THINKING_TOP_K = 40


def _vlm_temperature(*, enable_thinking: bool, markdown: bool = False) -> float:
    """NuExtract docs: 0.2 non-thinking; 0.6 thinking extraction; 0.7 thinking markdown."""
    if not enable_thinking:
        return 0.2
    return 0.7 if markdown else 0.6


def _apply_vlm_generation_kwargs(
    payload: dict[str, Any],
    *,
    enable_thinking: bool,
    markdown: bool = False,
) -> None:
    payload["temperature"] = _vlm_temperature(enable_thinking=enable_thinking, markdown=markdown)
    if enable_thinking:
        payload["top_p"] = _NUEXTRACT_THINKING_TOP_P
        payload["top_k"] = _NUEXTRACT_THINKING_TOP_K


def strip_vlm_thinking(raw: str) -> str:
    """Drop NuExtract reasoning wrapper when thinking mode is enabled."""
    if "</think>" in raw:
        return raw.split("</think>", 1)[1].strip()
    return raw.strip()


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
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        hint = f"{field.name} {field.description}".lower()
        if isinstance(value, (int, float)) and any(token in hint for token in _MONEY_HINTS):
            value = f"{float(value):.2f}"
        rows.append(
            {
                "name": field.name,
                "value": "" if value is None else str(value),
                "confidence": 0.9 if value is not None else None,
            }
        )
    return json.dumps({"fields": rows}, ensure_ascii=False)


def _structured_payload(
    *,
    spec: DocumentModelSpec,
    content: list[dict[str, Any]],
    schema: list[SchemaFieldSpec],
    extraction_instructions: str,
    settings: Settings,
) -> dict[str, Any]:
    template = build_vlm_template(schema)
    instructions = build_vlm_instructions(
        schema,
        document_instructions=extraction_instructions,
    )
    field_count = sum(1 for field in schema if field.name.strip())
    enable_thinking = settings.repody_vlm_enable_thinking
    payload: dict[str, Any] = {
        "model": spec.runtime_model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": vlm_max_tokens_for_field_count(
            field_count,
            ceiling=settings.repody_vlm_max_tokens,
            enable_thinking=enable_thinking,
        ),
        "stream": False,
        "chat_template_kwargs": {
            "template": json.dumps(template, ensure_ascii=False),
            "enable_thinking": enable_thinking,
        },
    }
    _apply_vlm_generation_kwargs(payload, enable_thinking=enable_thinking)
    if instructions:
        payload["chat_template_kwargs"]["instructions"] = instructions
    return payload


def _markdown_payload(
    *,
    spec: DocumentModelSpec,
    content: list[dict[str, Any]],
    page_count: int,
    settings: Settings,
) -> dict[str, Any]:
    enable_thinking = settings.repody_vlm_enable_thinking
    payload: dict[str, Any] = {
        "model": spec.runtime_model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": vlm_max_tokens_for_markdown(
            page_count=page_count,
            ceiling=settings.repody_vlm_markdown_max_tokens,
            enable_thinking=enable_thinking,
        ),
        "stream": False,
        "chat_template_kwargs": {
            "mode": "markdown",
            "enable_thinking": enable_thinking,
        },
    }
    _apply_vlm_generation_kwargs(payload, enable_thinking=enable_thinking, markdown=True)
    return payload
