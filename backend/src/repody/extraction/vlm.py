"""Repody VLM adapters — local llama-server + NuExtract cloud.

Flow (local):
  1. prepare_nuextract_pages → encode_pages_as_image_urls
  2. structured and/or markdown chat.completions
  3. store raw model JSON; project leaves for UI/rules
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import structlog

from repody.catalog.adapters import register_document_model_adapter
from repody.catalog.registry import DocumentModelSpec, parse_document_model
from repody.extraction.branding import (
    REPODY_VLM_CATALOG_ID,
    REPODY_VLM_CLOUD_CATALOG_ID,
)
from repody.extraction.fields import fields_from_nuextract_json
from repody.extraction.nuextract import (
    build_nuextract_instructions,
    build_nuextract_template,
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
from repody.inference.nuextract_cloud import (
    NuExtractCloudConfig,
    NuExtractCloudError,
    extract_structured as nuextract_extract_structured,
)
from repody.inference.openai_compat import post_chat_completion
from repody.inference.runtime import llamacpp_base_url
from repody.settings import Settings, get_settings

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
    text = strip_thinking(str(data["choices"][0]["message"]["content"]))
    return text or None


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
    _ = document_type
    settings = get_settings()
    spec = spec or parse_document_model(None)
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
    want_markdown = bool(markdown_extraction and settings.repody_vlm_markdown_on_extract)
    thinking = bool(settings.repody_vlm_enable_thinking)

    # Markdown-only (no schema fields).
    if want_markdown and not has_schema:
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
    raw = strip_thinking(str(data["choices"][0]["message"]["content"]))
    fields = fields_from_nuextract_json(raw, schema)

    markdown_text = None
    if want_markdown:
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


def _cloud_config(settings: Settings) -> NuExtractCloudConfig:
    api_key = (settings.nuextract_cloud_api_key or "").strip()
    if not api_key:
        raise NuExtractCloudError(
            "NuExtract cloud is enabled but AUDIT_NUEXTRACT_CLOUD_API_KEY is not set."
        )
    return NuExtractCloudConfig(
        api_key=api_key,
        base_url=(settings.nuextract_cloud_base_url or "https://nuextract.ai").rstrip("/"),
        timeout_seconds=float(settings.nuextract_cloud_timeout_seconds),
        project_id=(settings.nuextract_cloud_project_id or "").strip() or None,
    )


async def extract_with_repody_vlm_cloud(
    bundle: DocumentBundle,
    schema: list[SchemaFieldSpec],
    document_type: str,
    *,
    spec: DocumentModelSpec | None = None,
    extraction_instructions: str = "",
    markdown_extraction: bool = False,
    extraction_icl_examples: list[ExtractionIclExample] | None = None,
) -> ExtractionResult:
    """Structured extraction via the NuExtract platform API."""
    _ = document_type
    _ = extraction_icl_examples  # cloud REST does not accept ICL pairs yet
    settings = get_settings()
    spec = spec or parse_document_model(None)
    has_schema = any(field.name.strip() for field in schema)

    if markdown_extraction and not has_schema:
        raise NuExtractCloudError(
            "NuExtract cloud adapter does not support markdown-only extraction yet. "
            "Use local Repody VLM (repody:vlm) or add structured schema fields."
        )
    if not has_schema:
        raise NuExtractCloudError(
            "NuExtract cloud structured extraction requires at least one schema field."
        )

    started = time.perf_counter()
    output = await nuextract_extract_structured(
        _cloud_config(settings),
        template=build_nuextract_template(schema),
        file_bytes=bundle.raw_bytes,
        mime_type=bundle.mime_type or "application/octet-stream",
        instructions=build_nuextract_instructions(
            schema, document_instructions=extraction_instructions
        ),
    )
    result_json = json.dumps(output.result, ensure_ascii=False)
    raw = output.raw_model_output or result_json
    model_json = raw if raw.strip().startswith("{") else result_json
    fields = fields_from_nuextract_json(model_json, schema)

    log.info(
        "repody_vlm_cloud_done",
        runtime=spec.runtime,
        model=spec.runtime_model,
        project_id=output.project_id,
        job_id=output.job_id,
        input_tokens=output.input_tokens,
        output_tokens=output.output_tokens,
        elapsed_ms=int((time.perf_counter() - started) * 1000),
        extracted=sum(1 for field in fields if field.extracted),
    )
    return ExtractionResult(
        fields=fields or empty_fields_from_schema(schema),
        raw_text=raw,
        pages_rendered=bundle.page_count or 1,
        pages_sent=1,
        pages_dropped=0,
    )


register_document_model_adapter(REPODY_VLM_CATALOG_ID, extract_with_repody_vlm)
register_document_model_adapter(REPODY_VLM_CLOUD_CATALOG_ID, extract_with_repody_vlm_cloud)
