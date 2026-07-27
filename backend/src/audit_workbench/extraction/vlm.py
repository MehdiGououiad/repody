"""Repody VLM local and cloud extraction adapters."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import structlog

from audit_workbench.catalog.adapters import register_document_model_adapter
from audit_workbench.catalog.registry import DocumentModelSpec, parse_document_model
from audit_workbench.extraction.branding import (
    REPODY_VLM_CATALOG_ID,
    REPODY_VLM_CLOUD_CATALOG_ID,
)
from audit_workbench.extraction.nuextract import (
    NUEXTRACT_ENABLE_THINKING,
    NUEXTRACT_MAX_PAGES_PER_REQUEST,
    build_vlm_template,
)
from audit_workbench.extraction.payloads import (
    _fields_payload,
    _markdown_payload,
    _structured_payload,
    build_vlm_instructions,
    strip_vlm_thinking,
)
from audit_workbench.extraction.render import (
    _encode_pages_for_vlm,
    _vlm_pages,
    cap_vlm_pages,
    pages_dropped,
)
from audit_workbench.extraction.parse import parse_fields_json
from audit_workbench.extraction.schema import empty_fields_from_schema
from audit_workbench.extraction.types import (
    DocumentBundle,
    ExtractionIclExample,
    ExtractionResult,
    SchemaFieldSpec,
)
from audit_workbench.inference.nuextract_cloud import (
    NuExtractCloudClient,
    NuExtractCloudConfig,
    NuExtractCloudError,
)
from audit_workbench.inference.openai_compat import post_chat_completion
from audit_workbench.inference.runtime import llamacpp_base_url
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
    pages, _ = cap_vlm_pages(all_pages, max_pages=max_pages)
    # PDF render already caps rasterization; use total page count for telemetry.
    dropped = pages_dropped(rendered=pages_rendered, sent=len(pages))
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
    """Extract structured fields using the NuExtract platform API."""
    _ = document_type
    _ = extraction_icl_examples
    settings = get_settings()
    spec = spec or parse_document_model(None)
    has_schema_fields = any(field.name.strip() for field in schema)

    if markdown_extraction and not has_schema_fields:
        raise NuExtractCloudError(
            "NuExtract cloud adapter does not support markdown-only extraction yet. "
            "Use local Repody VLM (repody:vlm) or add structured schema fields."
        )
    if not has_schema_fields:
        raise NuExtractCloudError(
            "NuExtract cloud structured extraction requires at least one schema field."
        )

    template = build_vlm_template(schema)
    instructions = build_vlm_instructions(
        schema,
        document_instructions=extraction_instructions,
    )
    client = NuExtractCloudClient(_cloud_config(settings))

    started = time.perf_counter()
    output = await client.extract_structured(
        template=template,
        file_bytes=bundle.raw_bytes,
        mime_type=bundle.mime_type or "application/octet-stream",
        instructions=instructions,
    )
    result_json = json.dumps(output.result, ensure_ascii=False)
    raw = output.raw_model_output or result_json
    fields = parse_fields_json(_fields_payload(result_json, schema), schema)

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
        markdown_text=None,
        pages_rendered=bundle.page_count or 1,
        pages_sent=1,
        pages_dropped=0,
    )
# Catalog adapter registration (side-effect on import)
# Catalog adapter registration (side-effect on import)
register_document_model_adapter(REPODY_VLM_CATALOG_ID, extract_with_repody_vlm)
register_document_model_adapter(REPODY_VLM_CLOUD_CATALOG_ID, extract_with_repody_vlm_cloud)
