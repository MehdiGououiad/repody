"""Extract one document: page images -> the model -> one value per field, or Markdown.

Documents with fields go to NuExtract (structured mode). Documents without fields are transcribed to
Markdown by AUDIT_MARKDOWN_PROVIDER: NuExtract's markdown mode (all pages in one request) or
LightOnOCR-3 (one request per page).

Answers are cached in Redis by document bytes, request (provider, model, template, instructions,
examples) and rendering (page limit, resolution) when AUDIT_EXTRACTION_CACHE_TTL_SECONDS > 0.
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

from repody.extraction import client, lightonocr, nuextract, render
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


def _uses_lightonocr(doc: DocumentDef) -> bool:
    return not doc.schema_fields and get_settings().markdown_provider == "lightonocr"


def _request(doc: DocumentDef) -> dict[str, Any]:
    """The request that decides the answer, without the page images."""
    settings = get_settings()
    if doc.schema_fields:
        return nuextract.structured_request(doc, settings.llamacpp_served_model)
    if _uses_lightonocr(doc):
        return lightonocr.request(settings.lightonocr_served_model)
    return nuextract.markdown_request(settings.llamacpp_served_model)


def _cache_key(data: bytes, request: dict[str, Any]) -> str:
    """Everything that decides the answer: the file, the request, and how pages are rendered."""
    rendering = {
        "max_pages": get_settings().max_pages_per_document,
        "pdf_dpi": render.PDF_DPI,
        "lightonocr": (lightonocr.PDF_DPI, lightonocr.LONGEST_EDGE),
    }
    meta = json.dumps({"request": request, "rendering": rendering}, sort_keys=True)
    return f"extract:{hashlib.sha256(data + meta.encode()).hexdigest()}"


def _with_pages(request: dict[str, Any], parts: list[dict[str, Any]]) -> dict[str, Any]:
    """A copy of ``request`` whose last (user) message holds the page images."""
    return {**request, "messages": [*request["messages"][:-1], {"role": "user", "content": parts}]}


async def _ask_model(doc: DocumentDef, data: bytes, mime: str, request: dict[str, Any]) -> _Answer:
    settings = get_settings()
    max_pages = settings.max_pages_per_document
    if _uses_lightonocr(doc):
        # One request per page, as LightOn's client does; pages joined by a blank line.
        parts, total = await asyncio.to_thread(
            lightonocr.page_parts, data, mime, max_pages=max_pages
        )
        replies = await asyncio.gather(
            *(
                client.chat(
                    _with_pages(request, [part]),
                    base_url=settings.lightonocr_base_url,
                    api_key=settings.lightonocr_api_key.get_secret_value(),
                )
                for part in parts
            )
        )
    else:
        parts, total = await asyncio.to_thread(
            nuextract.page_parts, data, mime, max_pages=max_pages
        )
        replies = [await client.chat(_with_pages(request, parts))]
    text = "\n\n".join(reply.text for reply in replies)
    truncated = any(reply.truncated for reply in replies)
    pages = {"pages_rendered": total, "pages_sent": len(parts), "truncated": truncated}
    if doc.schema_fields:
        return _Answer(answer=text, **pages)
    if not text:
        raise RuntimeError("The model returned no Markdown for the document.")
    return _Answer(markdown=text[:MAX_TEXT_CHARS], **pages)


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
        model="lightonocr" if _uses_lightonocr(doc) else "nuextract",
        ms=elapsed,
        cache_hit=meta.cache_hit,
        fields=meta.fields_extracted,
        pages=answer.pages_sent,
        error=error,
    )
    return fields, meta
