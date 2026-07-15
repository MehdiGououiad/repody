from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog

from audit_workbench.catalog.registry import DocumentModelSpec, parse_document_model
from audit_workbench.extraction.base import ExtractionIclExample, ExtractionResult, SchemaFieldSpec
from audit_workbench.extraction.document_bundle import DocumentBundle
from audit_workbench.extraction.field_json import parse_fields_json
from audit_workbench.extraction.schema_fields import empty_fields_from_schema
from audit_workbench.extraction.repody_vlm_pages import _encode_pages_for_vlm, _vlm_pages, cap_vlm_pages
from audit_workbench.extraction.repody_vlm_payloads import (
    _fields_payload,
    _markdown_payload,
    _structured_payload,
    strip_vlm_thinking,
)
from audit_workbench.inference.openai_compat import post_chat_completion
from audit_workbench.inference.runtime import llamacpp_base_url
from audit_workbench.extraction.nuextract_contract import (
    NUEXTRACT_ENABLE_THINKING,
    NUEXTRACT_MAX_PAGES_PER_REQUEST,
)
from audit_workbench.settings import Settings, get_settings

log = structlog.get_logger()


async def _fetch_repody_vlm_markdown(
    base_url: str,
    payload: dict[str, Any],
    *,
    settings: Settings,
) -> str | None:
    try:
        data = await post_chat_completion(
            base_url,
            payload,
            timeout=settings.repody_vlm_timeout_seconds,
        )
    except Exception as exc:
        log.warning("repody_vlm_markdown_failed", error=repr(exc))
        return None
    raw = strip_vlm_thinking(str(data["choices"][0]["message"]["content"]))
    return raw or None


async def extract_with_repody_vlm(
    bundle: DocumentBundle,
    schema: list[SchemaFieldSpec],
    document_type: str,
    *,
    spec: DocumentModelSpec | None = None,
    extraction_instructions: str = "",
    markdown_extraction: bool = False,
    extraction_icl_examples: list[ExtractionIclExample] | None = None,
) -> ExtractionResult:
    settings = get_settings()
    spec = spec or parse_document_model(None)
    base_url = llamacpp_base_url(settings)
    all_pages, pages_rendered = _vlm_pages(bundle)
    max_pages = NUEXTRACT_MAX_PAGES_PER_REQUEST
    pages, dropped = cap_vlm_pages(all_pages, max_pages=max_pages)
    if dropped:
        log.warning(
            "repody_vlm_pages_capped",
            rendered=pages_rendered,
            sent=len(pages),
            dropped=dropped,
            max_pages=max_pages,
        )

    content = await asyncio.to_thread(_encode_pages_for_vlm, pages)
    has_schema_fields = any(field.name.strip() for field in schema)
    markdown_only = (
        markdown_extraction
        and settings.repody_vlm_markdown_on_extract
        and not has_schema_fields
    )
    markdown_payload = (
        _markdown_payload(
            spec=spec,
            content=content,
        )
        if markdown_only
        else None
    )

    if markdown_payload is not None:
        started = time.perf_counter()
        markdown_text = await _fetch_repody_vlm_markdown(
            base_url,
            markdown_payload,
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
            thinking=NUEXTRACT_ENABLE_THINKING,
            markdown_chars=len(markdown_text or ""),
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )
        return ExtractionResult(
            fields=empty_fields_from_schema(schema),
            raw_text=None,
            markdown_text=markdown_text,
            pages_rendered=pages_rendered,
            pages_sent=len(pages),
            pages_dropped=dropped,
        )

    structured_payload = _structured_payload(
        spec=spec,
        content=content,
        schema=schema,
        extraction_instructions=extraction_instructions,
        extraction_icl_examples=extraction_icl_examples,
    )

    started = time.perf_counter()
    data = await post_chat_completion(
        base_url,
        structured_payload,
        timeout=settings.repody_vlm_timeout_seconds,
    )
    markdown_text = None

    raw = strip_vlm_thinking(str(data["choices"][0]["message"]["content"]))
    fields = parse_fields_json(_fields_payload(raw, schema), schema)
    timings = data.get("timings") or {}
    log.info(
        "repody_vlm_done",
        runtime=spec.runtime,
        model=spec.runtime_model,
        pages=len(pages),
        pages_rendered=pages_rendered,
        pages_dropped=dropped,
        max_tokens=structured_payload.get("max_tokens"),
        markdown=False,
        thinking=NUEXTRACT_ENABLE_THINKING,
        markdown_chars=0,
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
