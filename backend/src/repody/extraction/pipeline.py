"""Extract one document: page images -> the model -> one value per field, or Markdown.

Everything goes to NuExtract3, all pages in one request: documents with fields in structured
mode, documents without fields in its Markdown mode.

Answers are cached in Redis by document bytes, request (model, template, instructions, examples)
and rendering (page limit, resolution) when AUDIT_EXTRACTION_CACHE_TTL_SECONDS > 0.
The cache is optional: when Redis fails, the model is asked and the failure logged.
"""

import asyncio
import hashlib
import json
import time
from typing import Any

import structlog
from pydantic import BaseModel
from redis.exceptions import RedisError

from repody.extraction import client, nuextract, render
from repody.extraction.fields import FieldValue, leaf_values, parse_answer
from repody.infra.redis import get_redis
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
    model = get_settings().llamacpp_served_model
    if doc.schema_fields:
        return nuextract.structured_request(doc, model)
    return nuextract.markdown_request(model)


def _cache_key(data: bytes, request: dict[str, Any]) -> str:
    """Everything that decides the answer: the file, the request, and how pages are rendered."""
    rendering = {"max_pages": get_settings().max_pages_per_document, "pdf_dpi": render.PDF_DPI}
    meta = json.dumps({"request": request, "rendering": rendering}, sort_keys=True)
    return f"extract:{hashlib.sha256(data + meta.encode()).hexdigest()}"


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


async def _cached(key: str) -> _Answer | None:
    try:
        cached = await get_redis().get(key)
    except RedisError as exc:
        log.warning("extraction_cache_unavailable", error=repr(exc))
        return None
    return _Answer.model_validate_json(cached) if cached else None


async def _cache(key: str, answer: _Answer, ttl: int) -> None:
    try:
        await get_redis().set(key, answer.model_dump_json(), ex=ttl)
    except RedisError as exc:
        log.warning("extraction_cache_unavailable", error=repr(exc))


async def extract(
    doc: DocumentDef, data: bytes, mime: str
) -> tuple[list[FieldValue], ExtractionMeta]:
    request = _request(doc)
    key = _cache_key(data, request)
    ttl = get_settings().extraction_cache_ttl_seconds

    started = time.perf_counter()
    cached = await _cached(key) if ttl else None
    answer = cached or await _ask_model(doc, data, mime, request)
    if ttl and cached is None:
        await _cache(key, answer, ttl)
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
        cache_hit=cached is not None,
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
        cache_hit=meta.cache_hit,
        fields=meta.fields_extracted,
        pages=answer.pages_sent,
        error=error,
    )
    return fields, meta
