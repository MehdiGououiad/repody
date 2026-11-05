"""Extract one document: page images -> the model -> one value per field, or Markdown.

Documents with fields go to NuExtract (structured mode). Documents without fields are transcribed to
Markdown by AUDIT_MARKDOWN_PROVIDER: NuExtract's markdown mode (all pages in one request) or
LightOnOCR-3 (one request per page).

Answers are cached in Redis by document bytes and request (provider, model, template, instructions,
examples) when AUDIT_EXTRACTION_CACHE_TTL_SECONDS > 0.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from typing import Any

import structlog
from pydantic import BaseModel

from repody.extraction import client, lightonocr, nuextract
from repody.extraction.fields import FieldValue, leaf_values
from repody.extraction.render import page_images
from repody.infra.redis import get_redis
from repody.schemas.run import ExtractionMeta
from repody.schemas.workflow import DocumentDef
from repody.settings import get_settings

log = structlog.get_logger(__name__)

MAX_TEXT_CHARS = 80_000


class _Answer(BaseModel):
    answer: str | None = None  # structured JSON
    markdown: str | None = None
    pages_rendered: int = 0
    pages_sent: int = 0


def _uses_lightonocr(doc: DocumentDef) -> bool:
    return not doc.schema_fields and get_settings().markdown_provider == "lightonocr"


def _request(doc: DocumentDef) -> dict[str, Any]:
    """The request that decides the answer, without the page images (also the cache key)."""
    settings = get_settings()
    if doc.schema_fields:
        return nuextract.structured_request(doc, settings.llamacpp_served_model)
    if _uses_lightonocr(doc):
        return lightonocr.request(settings.lightonocr_served_model)
    return nuextract.markdown_request(settings.llamacpp_served_model)


async def _ask_nuextract(data: bytes, mime: str, request: dict) -> tuple[str, int, int]:
    """All pages in one request, as NuExtract's model card sends a multi-page PDF."""
    images, total = await asyncio.to_thread(
        page_images, data, mime, max_pages=get_settings().max_pages_per_document
    )
    request["messages"][-1]["content"] = images
    return await client.chat(request), total, len(images)


async def _ask_lightonocr(data: bytes, mime: str, request: dict) -> tuple[str, int, int]:
    """One request per page, as LightOn's client does; pages joined by a blank line."""
    settings = get_settings()
    pages, total = await asyncio.to_thread(
        lightonocr.page_images, data, mime, max_pages=settings.max_pages_per_document
    )
    texts = []
    for page in pages:
        request["messages"][0]["content"] = [lightonocr.image_part(page)]
        texts.append(
            await client.chat(
                request, base_url=settings.lightonocr_base_url, api_key=settings.lightonocr_api_key
            )
        )
    return "\n\n".join(texts), total, len(pages)


async def _ask_model(doc: DocumentDef, data: bytes, mime: str, request: dict) -> _Answer:
    ask = _ask_lightonocr if _uses_lightonocr(doc) else _ask_nuextract
    text, total, sent = await ask(data, mime, request)
    if doc.schema_fields:
        return _Answer(answer=text, pages_rendered=total, pages_sent=sent)
    if not text:
        raise RuntimeError("The model returned no Markdown for the document.")
    return _Answer(markdown=text[:MAX_TEXT_CHARS], pages_rendered=total, pages_sent=sent)


async def extract(
    doc: DocumentDef, data: bytes, mime: str
) -> tuple[list[FieldValue], ExtractionMeta]:
    request = _request(doc)
    digest = hashlib.sha256(data + json.dumps(request, sort_keys=True).encode()).hexdigest()
    key = f"extract:{digest}"
    ttl = get_settings().extraction_cache_ttl_seconds

    started = time.perf_counter()
    cached = await get_redis().get(key) if ttl else None
    answer = (
        _Answer.model_validate_json(cached)
        if cached
        else await _ask_model(doc, data, mime, request)
    )
    if ttl and not cached:
        await get_redis().set(key, answer.model_dump_json(), ex=ttl)
    elapsed = int((time.perf_counter() - started) * 1000)

    fields = leaf_values(doc.schema_fields, answer.answer)
    meta = ExtractionMeta(
        extraction_ms=elapsed,
        cache_hit=cached is not None,
        fields_extracted=sum(f.extracted for f in fields),
        pages_rendered=answer.pages_rendered,
        pages_sent=answer.pages_sent,
        raw_text=answer.answer[:MAX_TEXT_CHARS] if answer.answer else None,
        markdown_text=answer.markdown,
    )
    log.info(
        "document_extracted",
        document_type=doc.document_type,
        model="lightonocr" if _uses_lightonocr(doc) else "nuextract",
        ms=elapsed,
        cache_hit=meta.cache_hit,
        fields=meta.fields_extracted,
        pages=answer.pages_sent,
    )
    return fields, meta
