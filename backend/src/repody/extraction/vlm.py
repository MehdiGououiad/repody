"""Repody VLM - NuExtract3 on an OpenAI-compatible llama-server.

Flow (local):
  1. prepare_nuextract_pages -> encode_pages_as_image_urls
  2. structured and/or markdown chat.completions
  3. store raw model JSON; project leaves for UI/rules
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

import structlog

from repody.extraction.fields import fields_from_nuextract_json
from repody.extraction.nuextract import (
    markdown_chat_payload,
    strip_thinking,
    structured_chat_payload,
)
from repody.extraction.render import (
    encode_pages_as_image_urls,
    pages_dropped,
    prepare_nuextract_pages,
)
from repody.extraction.schema import empty_fields_from_schema
from repody.extraction.types import (
    DocumentBundle,
    ExtractionIclExample,
    ExtractionResult,
    SchemaFieldSpec,
)
from repody.inference.openai_compat import message_content, post_chat_completion
from repody.inference.runtime import llamacpp_base_url
from repody.settings import Settings, get_settings

if TYPE_CHECKING:
    from repody.catalog.registry import DocumentModelSpec

log = structlog.get_logger()


async def _chat(
    base_url: str,
    payload: dict[str, Any],
    *,
    settings: Settings,
) -> dict[str, Any]:
    return await post_chat_completion(
        base_url,
        payload,
        timeout=settings.repody_vlm_timeout_seconds,
    )


async def _markdown(
    base_url: str,
    payload: dict[str, Any],
    *,
    settings: Settings,
) -> str | None:
    try:
        data = await _chat(base_url, payload, settings=settings)
    except Exception as exc:
        log.warning("repody_vlm_markdown_failed", error=repr(exc))
        return None
    text = strip_thinking(message_content(data))
    return text or None


async def extract_with_repody_vlm(
    bundle: DocumentBundle,
    schema: list[SchemaFieldSpec],
    document_type: str,
    *,
    spec: DocumentModelSpec,
    extraction_instructions: str = "",
    markdown_extraction: bool = False,
    extraction_icl_examples: list[ExtractionIclExample] | None = None,
) -> ExtractionResult:
    _ = document_type
    settings = get_settings()
    base_url = llamacpp_base_url(settings)
    max_pages = settings.repody_vlm_max_pages_per_request

    pages, pages_rendered = prepare_nuextract_pages(bundle, max_pages=max_pages)
    dropped = pages_dropped(rendered=pages_rendered, sent=len(pages))
    if dropped:
        log.warning(
            "repody_vlm_pages_capped",
            rendered=pages_rendered,
            sent=len(pages),
            dropped=dropped,
            max_pages=max_pages,
        )

    content = await asyncio.to_thread(encode_pages_as_image_urls, pages)
    has_schema = any(field.name.strip() for field in schema)
    markdown_only = bool(markdown_extraction and not has_schema)
    want_dual_markdown = bool(
        markdown_extraction and has_schema and settings.repody_vlm_markdown_on_extract
    )
    thinking = bool(settings.repody_vlm_enable_thinking)

    # Markdown-only (no schema fields) - one official NuExtract call.
    if markdown_only:
        started = time.perf_counter()
        markdown_text = await _markdown(
            base_url,
            markdown_chat_payload(model=spec.runtime_model, content=content),
            settings=settings,
        )
        if not (markdown_text or "").strip():
            raise RuntimeError(
                "NuExtract markdown extraction returned no text. "
                "Start host inference (pnpm llamacpp:serve) and ensure workers can reach "
                "AUDIT_LLAMACPP_BASE_URL / host.docker.internal:8081."
            )
        log.info(
            "repody_vlm_done",
            runtime=spec.runtime,
            model=spec.runtime_model,
            pages=len(pages),
            pages_rendered=pages_rendered,
            pages_dropped=dropped,
            markdown=True,
            markdown_only=True,
            thinking=thinking,
            markdown_chars=len(markdown_text or ""),
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )
        return ExtractionResult(
            fields=empty_fields_from_schema(schema),
            markdown_text=markdown_text,
            pages_rendered=pages_rendered,
            pages_sent=len(pages),
            pages_dropped=dropped,
        )

    if not has_schema:
        return ExtractionResult(
            fields=empty_fields_from_schema(schema),
            pages_rendered=pages_rendered,
            pages_sent=len(pages),
            pages_dropped=dropped,
        )

    # Structured extraction (official template JSON is source of truth).
    started = time.perf_counter()
    data = await _chat(
        base_url,
        structured_chat_payload(
            model=spec.runtime_model,
            content=content,
            schema=schema,
            extraction_instructions=extraction_instructions,
            extraction_icl_examples=extraction_icl_examples,
        ),
        settings=settings,
    )
    raw = strip_thinking(message_content(data))
    fields = fields_from_nuextract_json(raw, schema)

    markdown_text = None
    if want_dual_markdown:
        markdown_text = await _markdown(
            base_url,
            markdown_chat_payload(model=spec.runtime_model, content=content),
            settings=settings,
        )

    timings = data.get("timings") or {}
    log.info(
        "repody_vlm_done",
        runtime=spec.runtime,
        model=spec.runtime_model,
        pages=len(pages),
        pages_rendered=pages_rendered,
        pages_dropped=dropped,
        markdown=bool(markdown_text),
        thinking=thinking,
        markdown_chars=len(markdown_text or ""),
        elapsed_ms=int((time.perf_counter() - started) * 1000),
        prompt_ms=int(timings.get("prompt_ms") or 0),
        predicted_ms=int(timings.get("predicted_ms") or 0),
        output_tokens=(data.get("usage") or {}).get("completion_tokens"),
        extracted=sum(1 for field in fields if field.extracted),
    )
    return ExtractionResult(
        fields=fields,
        raw_text=raw,
        markdown_text=markdown_text,
        pages_rendered=pages_rendered,
        pages_sent=len(pages),
        pages_dropped=dropped,
    )
