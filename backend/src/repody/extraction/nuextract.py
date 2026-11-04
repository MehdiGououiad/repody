"""NuExtract3 requests, as ``chat.completions.create`` arguments: the template, instructions
and in-context examples go to llama-server's chat template (``chat_template_kwargs``).

https://huggingface.co/numind/NuExtract3-GGUF · https://github.com/numindai/nuextract
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from repody.schemas.workflow import DocumentDef, SchemaField

STRUCTURED_TEMPERATURE = 0.2
EXACT_TEMPERATURE = 0.0  # the official in-context and Markdown examples use 0
LIST_SUFFIX = "-list"  # platform spelling of a list type: `number-list` is `["number"]`


def _choices(field: SchemaField) -> list[str]:
    if len(field.enum_values) < 2:
        raise ValueError(f"{field.template_type} field {field.name!r} needs at least 2 choices")
    return field.enum_values


def template_node(field: SchemaField) -> Any:
    """The NuExtract template value for one field (recursive for objects)."""
    match field.template_type:
        case "object":
            return template(field.children)
        case "object-array":
            return [template(field.children)]
        case "enum":
            return _choices(field)
        case "multi-enum":
            return [_choices(field)]
        case kind if kind.endswith(LIST_SUFFIX) and kind != LIST_SUFFIX:
            return [kind.removesuffix(LIST_SUFFIX)]
        case kind:
            return kind


def template(fields: list[SchemaField]) -> dict[str, Any]:
    return {field.name: template_node(field) for field in fields if field.name}


def _field_notes(fields: list[SchemaField], prefix: str = "") -> Iterator[str]:
    for field in fields:
        if not field.name:
            continue
        path = f"{prefix}{field.name}"
        if field.description:
            yield f"- {path}: {field.description}"
        yield from _field_notes(field.children, f"{path}.")


def instructions(doc: DocumentDef) -> str:
    """Free-text instructions: the document's notes, then each field's description."""
    notes = list(_field_notes(doc.schema_fields))
    blocks = [
        doc.extraction_instructions.strip(),
        "\n".join(["Field guidance:", *notes]) if notes else "",
    ]
    return "\n\n".join(block for block in blocks if block)


def structured_request(doc: DocumentDef, model: str) -> dict[str, Any]:
    """Request body without the page images (``messages[-1]`` gets them)."""
    examples = [ex for ex in doc.extraction_icl_examples if ex.input.strip() and ex.output.strip()]
    kwargs: dict[str, Any] = {
        "template": json.dumps(template(doc.schema_fields), ensure_ascii=False, indent=4),
        "enable_thinking": False,
    }
    if text := instructions(doc):
        kwargs["instructions"] = text
    return {
        "model": model,
        "temperature": EXACT_TEMPERATURE if examples else STRUCTURED_TEMPERATURE,
        "messages": [
            *(
                {
                    "role": "developer",
                    "content": [
                        {"type": "text", "text": ex.input.strip()},
                        {"type": "text", "text": ex.output.strip()},
                    ],
                }
                for ex in examples
            ),
            {"role": "user", "content": []},
        ],
        "extra_body": {"chat_template_kwargs": kwargs},
    }


def markdown_request(model: str) -> dict[str, Any]:
    return {
        "model": model,
        "temperature": EXACT_TEMPERATURE,
        "messages": [{"role": "user", "content": []}],
        "extra_body": {"chat_template_kwargs": {"mode": "markdown", "enable_thinking": False}},
    }
