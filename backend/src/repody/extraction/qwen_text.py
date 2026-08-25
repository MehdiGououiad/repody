"""Qwen text LLM → flat JSON for OCR+LLM structured extraction.

Thin adapter: OCR transcript + UI schema → one chat completion → leaf fields.
No document-specific heuristics and no post-hoc value rewriting.
"""

from __future__ import annotations

import re
from typing import Any

from repody.extraction.fields import fields_from_leaf_json
from repody.extraction.nuextract import resolve_template_type, strip_thinking
from repody.extraction.schema import iter_extraction_leaves
from repody.extraction.types import ExtractedFieldResult, SchemaFieldSpec
from repody.inference.openai_compat import post_chat_completion

_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)

_TYPE_HINTS = frozenset(
    {
        "date",
        "date-time",
        "time",
        "number",
        "integer",
        "boolean",
        "currency",
        "email-address",
        "phone-number",
        "iban",
        "object-array",
        "enum",
        "multi-enum",
    }
)


def _leaf_prompt_line(key: str, field: SchemaFieldSpec) -> str:
    desc = (field.description or key).strip()
    resolved = resolve_template_type(field.name, field.description, field.template_type)
    hints: list[str] = []
    if resolved in _TYPE_HINTS:
        hints.append(resolved)
    if field.enum_values:
        choices = ", ".join(field.enum_values[:12])
        if len(field.enum_values) > 12:
            choices += ", …"
        hints.append(f"choices: {choices}")
    hint_suffix = f" [{'; '.join(hints)}]" if hints else ""
    return f'- "{key}": {desc}{hint_suffix}'


def _max_tokens_for_schema(schema: list[SchemaFieldSpec]) -> int:
    leaf_count = len(iter_extraction_leaves(schema))
    return min(2048, max(256, 64 + leaf_count * 32))


def text_to_json_chat_payload(
    *,
    model: str,
    schema: list[SchemaFieldSpec],
    ocr_text: str,
    document_type: str,
    extraction_instructions: str = "",
) -> dict[str, Any]:
    """OpenAI chat payload for schema JSON from OCR text (Qwen3.5-friendly)."""
    leaves = iter_extraction_leaves(schema)
    keys = ", ".join(f'"{key}"' for key, _ in leaves)
    field_lines = "\n".join(_leaf_prompt_line(key, field) for key, field in leaves)
    system = (
        "/no_think\n"
        "Extract document fields from OCR text. "
        "Reply with one JSON object only. No markdown fences. No commentary. "
        f"Top-level keys must be exactly: {keys}. "
        "Use dotted keys for nested fields (e.g. \"address.city\"). "
        "For object-array fields return a JSON array of objects. "
        "Use empty string when unknown. "
        "Copy values from the OCR text only — do not invent, translate, "
        "normalize, correct, or reformat (including dates and IDs)."
    )
    instructions_block = ""
    if extraction_instructions.strip():
        instructions_block = f"Instructions:\n{extraction_instructions.strip()}\n\n"
    user = (
        f"Document type: {document_type or 'document'}.\n"
        f"{instructions_block}"
        f"Schema:\n{field_lines}\n\n"
        f"OCR text:\n{ocr_text}\n\n"
        "JSON:"
    )
    return {
        "model": model,
        "temperature": 0,
        "max_tokens": _max_tokens_for_schema(schema),
        "chat_template_kwargs": {"enable_thinking": False},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }


def parse_flat_json_response(raw: str) -> str:
    """Return JSON object string from model output (strip fences / thinking)."""
    cleaned = strip_thinking(raw).strip()
    match = _JSON_FENCE.search(cleaned)
    if match:
        cleaned = match.group(1).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    return cleaned


async def extract_fields_from_text(
    *,
    base_url: str,
    model: str,
    schema: list[SchemaFieldSpec],
    ocr_text: str,
    document_type: str,
    extraction_instructions: str = "",
    timeout: float,
) -> tuple[list[ExtractedFieldResult], str]:
    """Call Qwen (OpenAI-compatible) and project JSON onto schema leaves."""
    payload = text_to_json_chat_payload(
        model=model,
        schema=schema,
        ocr_text=ocr_text,
        document_type=document_type,
        extraction_instructions=extraction_instructions,
    )
    data = await post_chat_completion(base_url, payload, timeout=timeout)
    raw = str(data["choices"][0]["message"]["content"])
    json_text = parse_flat_json_response(raw)
    fields = fields_from_leaf_json(json_text, schema)
    return fields, json_text or raw
