"""Extract one document: page images -> the model -> one value per field, or Markdown.

Everything goes to NuExtract3, all pages in one request: documents with fields in structured
mode, documents without fields in its Markdown mode.
"""

import asyncio
import time
from typing import Any

import structlog
from pydantic import BaseModel

from repody.extraction import client, nuextract
from repody.extraction.fields import FieldValue, leaf_values, parse_answer
from repody.schemas.run import ExtractionMeta
from repody.schemas.workflow import DocumentDef
from repody.settings import get_settings

log = structlog.get_logger(__name__)

MAX_TEXT_CHARS = 80_000
TRUNCATED = "The model's answer was cut off at its token limit, so its fields are not used."


class _Answer(BaseModel):
    answer: str | None = None  # structured JSON
    markdown: str | None = None
    truncated: bool = False
    pages_rendered: int = 0
    pages_sent: int = 0


def _request(doc: DocumentDef) -> dict[str, Any]:
    """The request that decides the answer, without the page images."""
    settings = get_settings()
    model, max_tokens = settings.inference_model, settings.max_output_tokens
    if doc.schema_fields:
        return nuextract.structured_request(doc, model, max_tokens=max_tokens)
    return nuextract.markdown_request(model, max_tokens=max_tokens)


def _with_pages(request: dict[str, Any], parts: list[dict[str, Any]]) -> dict[str, Any]:
    """A copy of ``request`` whose last (user) message holds the page images."""
    return {**request, "messages": [*request["messages"][:-1], {"role": "user", "content": parts}]}


async def _ask_model(doc: DocumentDef, data: bytes, mime: str, request: dict[str, Any]) -> _Answer:
    parts, total = await asyncio.to_thread(
        nuextract.page_parts, data, mime, max_pages=get_settings().max_pages_per_document
    )
    reply = await client.chat(_with_pages(request, parts))
    pages = {"pages_rendered": total, "pages_sent": len(parts), "truncated": reply.truncated}
    if doc.schema_fields:
        return _Answer(answer=reply.text, **pages)
    if not reply.text:
        raise RuntimeError("The model returned no Markdown for the document.")
    return _Answer(markdown=reply.text[:MAX_TEXT_CHARS], **pages)


async def extract(
    doc: DocumentDef, data: bytes, mime: str
) -> tuple[list[FieldValue], ExtractionMeta]:
    started = time.perf_counter()
    answer = await _ask_model(doc, data, mime, _request(doc))
    elapsed = int((time.perf_counter() - started) * 1000)

    fields: list[FieldValue] = []
    error = TRUNCATED if answer.truncated else None
    if doc.schema_fields:
        # A cut-off answer can still parse as JSON (json-repair closes it), so it is not read.
        parsed, parse_error = ({}, None) if answer.truncated else parse_answer(answer.answer)
        error = error or parse_error
        fields = leaf_values(doc.schema_fields, parsed)
    meta = ExtractionMeta(
        extraction_ms=elapsed,
        fields_extracted=sum(f.extracted for f in fields),
        pages_rendered=answer.pages_rendered,
        pages_sent=answer.pages_sent,
        raw_text=answer.answer[:MAX_TEXT_CHARS] if answer.answer else None,
        markdown_text=answer.markdown,
        error=error,
    )
    log.info(
        "document_extracted",
        document_type=doc.document_type,
        model="nuextract",
        ms=elapsed,
        fields=meta.fields_extracted,
        pages=answer.pages_sent,
        error=error,
    )
    return fields, meta
