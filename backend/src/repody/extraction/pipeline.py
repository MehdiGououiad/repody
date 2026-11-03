"""Document extraction: Redis cache in front of NuExtract on the llama-server."""

from __future__ import annotations

import asyncio
import time

import structlog

from repody.extraction.cache import cache_key, get_cached, hash_bytes, set_cached
from repody.extraction.schema import empty_fields_from_schema, fields_from_sample_values
from repody.extraction.types import (
    DocumentBundle,
    ExtractionIclExample,
    ExtractionMetadata,
    ExtractionResult,
    SchemaFieldSpec,
    truncate_text,
)
from repody.extraction.vlm import extract_with_repody_vlm
from repody.inference.runtime import gpu_cold_start_likely
from repody.infra.observability.tracing import tracer
from repody.settings import get_settings

log = structlog.get_logger()


def extract_document_fields(
    schema: list[dict], *, sample_values: dict[str, str] | None = None
) -> list:
    """Dry run: schema placeholders, or caller-provided sample values (never invented data)."""
    specs = [SchemaFieldSpec.model_validate(row) for row in schema if isinstance(row, dict)]
    specs = [spec for spec in specs if spec.name]
    if sample_values:
        return fields_from_sample_values(specs, sample_values)
    return empty_fields_from_schema(specs)


def _metadata(
    result: ExtractionResult,
    *,
    extraction_ms: int,
    cache_hit: bool,
    markdown_extraction: bool,
) -> ExtractionMetadata:
    return ExtractionMetadata(
        extraction_ms=extraction_ms,
        cache_hit=cache_hit,
        gpu_cold_start_likely=not cache_hit and gpu_cold_start_likely(extraction_ms),
        fields_extracted=sum(1 for f in result.fields if f.extracted),
        markdown_extraction=markdown_extraction,
        markdown_text=truncate_text(result.markdown_text) if markdown_extraction else None,
        raw_text=truncate_text(result.raw_text),
        pages_rendered=result.pages_rendered,
        pages_sent=result.pages_sent,
        pages_dropped=result.pages_dropped,
    )


async def extract_document(
    document_bytes: bytes | None,
    mime_type: str,
    document_type: str,
    schema: list[SchemaFieldSpec],
    *,
    extraction_instructions: str = "",
    markdown_extraction: bool = False,
    extraction_icl_examples: list[ExtractionIclExample] | None = None,
) -> ExtractionResult:
    """Extract ``schema`` (and/or Markdown) from one document, reusing a cached result."""
    has_schema_fields = any(field.name.strip() for field in schema)
    if not document_bytes or (not has_schema_fields and not markdown_extraction):
        return ExtractionResult(fields=empty_fields_from_schema(schema))

    settings = get_settings()
    key = cache_key(
        content_hash=await asyncio.to_thread(hash_bytes, document_bytes),
        schema=schema,
        served_model=settings.llamacpp_served_model,
        markdown_extraction=markdown_extraction,
        extraction_instructions=extraction_instructions,
        icl_examples=extraction_icl_examples,
    )
    cached = await get_cached(key)
    if cached is not None:
        cached.meta = _metadata(
            cached, extraction_ms=0, cache_hit=True, markdown_extraction=markdown_extraction
        )
        return cached

    started = time.perf_counter()
    with tracer.start_as_current_span(
        "extraction.pipeline", attributes={"document_type": document_type}
    ):
        result = await extract_with_repody_vlm(
            DocumentBundle(raw_bytes=document_bytes, mime_type=mime_type),
            schema,
            extraction_instructions=extraction_instructions,
            markdown_extraction=markdown_extraction,
            extraction_icl_examples=extraction_icl_examples,
        )
    extraction_ms = int((time.perf_counter() - started) * 1000)
    result.meta = _metadata(
        result,
        extraction_ms=extraction_ms,
        cache_hit=False,
        markdown_extraction=markdown_extraction,
    )
    log.info(
        "pipeline_extracted",
        document_type=document_type,
        model=settings.llamacpp_served_model,
        ms=extraction_ms,
        fields=result.meta.fields_extracted,
    )
    await set_cached(key, result)
    return result
