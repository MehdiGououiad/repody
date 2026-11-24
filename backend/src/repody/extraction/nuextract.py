"""NuExtract3 requests, as ``chat.completions.create`` arguments, as the model card's vLLM
examples send them: the template, instructions and mode go to the chat template
(``chat_template_kwargs``), in-context examples as ``developer`` messages.

https://huggingface.co/numind/NuExtract3 ("vLLM inference") · https://github.com/numindai/nuextract
"""

import json
from collections.abc import Iterator
from typing import Any

from repody.extraction import render
from repody.schemas.catalog import scalar_type
from repody.schemas.workflow import DocumentDef, SchemaField

# The card's non-thinking mode, "for fast and deterministic extraction or Markdown conversion"
# ("temperature = 0.2"). Its document-to-Markdown code example uses 1, which measured worse on
# staging's vLLM (18 November, 11 hard pages: 96.1 at 1, 98.4 at 0.2; a handwritten invoice 73.9
# and 93.8). Structured answers were the same at 0.2 and 0 (16 documents, 234 fields).
TEMPERATURE = 0.2


def page_parts(
    data: bytes, mime: str, *, max_pages: int | None, area: float = 1.0
) -> tuple[list[dict[str, Any]], int]:
    """``(image parts, page count)``: PDF pages at 170 DPI and images as PNG (as the model
    card sends them; images upright, see ``render.open_image``), each at least
    ``render.MIN_MODEL_PIXELS``, then times ``area`` (a second read, repody.extraction.pipeline).

    All pages go in one request, as the model card sends a multi-page PDF.
    """
    if mime == "application/pdf":
        return render.pdf_page_parts(data, max_pages=max_pages, area=area)
    return [render.image_part(render.model_image(render.open_image(data), area))], 1


def template_node(field: SchemaField) -> Any:
    """The NuExtract template value for one field (recursive for objects)."""
    match field.template_type:
        case "object":
            return template(field.children)
        case "object-array":
            return [template(field.children)]
        case "enum":
            return field.enum_values  # at least 2 choices (SchemaField validates it)
        case "multi-enum":
            return [field.enum_values]
        case kind if scalar_type(kind) != kind:  # `number-list` is `["number"]`
            return [scalar_type(kind)]
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


def _has_list(fields: list[SchemaField]) -> bool:
    return any(
        field.template_type in ("object-array", "multi-enum")
        or scalar_type(field.template_type) != field.template_type
        or _has_list(field.children)
        for field in fields
    )


def _leaves(fields: list[SchemaField]) -> int:
    return sum(_leaves(field.children) if field.children else 1 for field in fields)


TOKENS_PER_FIELD = 256  # a long text value; most answers use a fraction of it


def answer_budget(doc: DocumentDef, max_tokens: int) -> int:
    """The longest answer a structured request may get: a schema without lists (tables, lists)
    has a known size, so an answer that loops stops early; one with lists gets ``max_tokens``."""
    if _has_list(doc.schema_fields):
        return max_tokens
    return min(max_tokens, TOKENS_PER_FIELD * (1 + _leaves(doc.schema_fields)))


def structured_request(doc: DocumentDef, model: str, *, max_tokens: int) -> dict[str, Any]:
    """Request body; the page images go in the last (user) message."""
    examples = [ex for ex in doc.extraction_icl_examples if ex.input.strip() and ex.output.strip()]
    kwargs: dict[str, Any] = {
        "template": json.dumps(template(doc.schema_fields), indent=4),  # as the card sends it
        "enable_thinking": False,
    }
    if text := instructions(doc):
        kwargs["instructions"] = text
    return {
        "model": model,
        "temperature": TEMPERATURE,
        "max_tokens": answer_budget(doc, max_tokens),
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


def markdown_request(model: str, *, max_tokens: int) -> dict[str, Any]:
    return {
        "model": model,
        "temperature": TEMPERATURE,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": []}],
        "extra_body": {"chat_template_kwargs": {"mode": "markdown", "enable_thinking": False}},
    }
