"""Extract one document: page images -> NuExtract on the llama-server -> one value per field.

Answers are cached in Redis by document bytes and request (model, template, instructions,
examples) when AUDIT_EXTRACTION_CACHE_TTL_SECONDS > 0.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time

import structlog
from pydantic import BaseModel

from repody.extraction import client, nuextract
from repody.extraction.fields import FieldValue, leaf_values
from repody.extraction.render import page_images
from repody.redis_pool import get_redis
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


async def _ask_model(doc: DocumentDef, data: bytes, request: dict) -> _Answer:
    settings = get_settings()
    images, total = await asyncio.to_thread(
        page_images, data, max_pages=settings.max_pages_per_document
    )
    request["messages"][-1]["content"] = images
    text = await client.chat(request)
    if doc.schema_fields:
        return _Answer(answer=text, pages_rendered=total, pages_sent=len(images))
    if not text:
        raise RuntimeError("NuExtract returned no Markdown for the document.")
    return _Answer(markdown=text[:MAX_TEXT_CHARS], pages_rendered=total, pages_sent=len(images))


async def extract(doc: DocumentDef, data: bytes) -> tuple[list[FieldValue], ExtractionMeta]:
    settings = get_settings()
    model = settings.llamacpp_served_model
    request = (
        nuextract.structured_request(doc, model)
        if doc.schema_fields
        else nuextract.markdown_request(model)
    )
    digest = hashlib.sha256(data + json.dumps(request, sort_keys=True).encode()).hexdigest()
    key = f"extract:{digest}"
    ttl = settings.extraction_cache_ttl_seconds

    started = time.perf_counter()
    cached = await get_redis().get(key) if ttl else None
    answer = _Answer.model_validate_json(cached) if cached else await _ask_model(doc, data, request)
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
        ms=elapsed,
        cache_hit=meta.cache_hit,
        fields=meta.fields_extracted,
        pages=answer.pages_sent,
    )
    return fields, meta
