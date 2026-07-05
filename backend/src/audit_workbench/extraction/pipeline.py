from __future__ import annotations

import asyncio
import time
from functools import lru_cache

import structlog

from audit_workbench.extraction.base import (
    DocumentExtractor,
    ExtractionMetadata,
    ExtractionResult,
    SchemaFieldSpec,
    truncate_ocr_text,
    truncate_text,
)
from audit_workbench.extraction.cache import (
    cache_key,
    cache_key_from_storage,
    get_cached,
    hash_bytes,
    schema_fingerprint,
    set_cached,
)
from audit_workbench.extraction.document_bundle import load_document_bundle
from audit_workbench.extraction.document_modes import (
    LOGIC_VALIDATION,
    parse_read_path,
    read_path_used_label,
    validation_mode_label,
)
from audit_workbench.extraction.gpu_cold_start import gpu_cold_start_likely
from audit_workbench.catalog.registry import (
    extract_with_document_model,
    normalize_model_id,
    parse_document_model,
)
import audit_workbench.extraction.repody_vlm  # noqa: F401 — register catalog adapters
from audit_workbench.extraction.schema_fields import empty_fields_from_schema
from audit_workbench.extraction.stub import StubDocumentExtractor
from audit_workbench.observability.tracing import start_span
from audit_workbench.settings import get_settings

log = structlog.get_logger()


@lru_cache
def get_extractor() -> DocumentExtractor:
    name = get_settings().extractor.lower()
    if name == "stub":
        return StubDocumentExtractor()
    return PipelineExtractor()


def _cached_result(
    cached: ExtractionResult,
    *,
    read_path_id: str,
    val_mode: str,
    model_id: str,
    document_type: str,
    content_hash: str | None = None,
    markdown_extraction: bool = False,
) -> ExtractionResult:
    used = cached.read_path_used or read_path_id
    log.info(
        "extraction_cache_hit",
        document_type=document_type,
        content_hash=(content_hash or "")[:12] or None,
        fields=sum(1 for f in cached.fields if f.extracted),
    )
    cached.meta = ExtractionMetadata(
        read_path_config=read_path_id,
        read_path_used=used,
        read_path_label=read_path_used_label(used),
        validation_mode=val_mode,
        validation_label=validation_mode_label(val_mode),
        document_model_id=model_id,
        extraction_ms=0,
        cache_hit=True,
        fields_extracted=sum(1 for f in cached.fields if f.extracted),
        markdown_extraction=markdown_extraction,
        ocr_text=truncate_ocr_text(cached.ocr_text) if markdown_extraction else None,
        raw_text=truncate_text(cached.raw_text),
    )
    return cached


class PipelineExtractor(DocumentExtractor):
    """Cache-aware extraction through the document model registry."""

    def __init__(self) -> None:
        self._settings = get_settings()

    async def extract(
        self,
        document_bytes: bytes | None,
        mime_type: str,
        document_type: str,
        schema: list[SchemaFieldSpec],
        *,
        extraction_mode: str = "document_model",
        document_model_id: str | None = None,
        storage_key: str | None = None,
        file_size: int | None = None,
        bundle: object | None = None,
        validation_mode: str = LOGIC_VALIDATION,
        extraction_instructions: str = "",
        markdown_extraction: bool = False,
    ) -> ExtractionResult:
        read_path = parse_read_path(extraction_mode)
        val_mode = (
            validation_mode
            if validation_mode in (LOGIC_VALIDATION, "logic_and_llm")
            else LOGIC_VALIDATION
        )
        if not document_bytes:
            return ExtractionResult(
                fields=empty_fields_from_schema(schema),
                raw_text=None,
            )

        settings = self._settings
        model_id = normalize_model_id(document_model_id or settings.default_document_model_id)
        model_spec = parse_document_model(model_id)
        has_schema_fields = any(field.name.strip() for field in schema)
        if not has_schema_fields and not markdown_extraction:
            return ExtractionResult(
                fields=empty_fields_from_schema(schema),
                raw_text=None,
            )
        if model_spec.read_path_id != read_path.id:
            read_path = parse_read_path(model_spec.read_path_id)
        cache_mode = (
            f"read:{read_path.id}:val:{val_mode}:md:{'1' if markdown_extraction else '0'}"
        )
        schema_fp = schema_fingerprint(schema)

        content_hash = await asyncio.to_thread(hash_bytes, document_bytes)

        if storage_key and file_size is not None:
            ck = cache_key_from_storage(
                storage_key=storage_key,
                file_size=file_size,
                content_hash=content_hash,
                schema_fp=schema_fp,
                extraction_mode=cache_mode,
                document_model_id=model_id,
                extractor=settings.extractor,
            )
            content_ck = cache_key(
                content_hash=content_hash,
                schema_fp=schema_fp,
                extraction_mode=cache_mode,
                document_model_id=model_id,
                extractor=settings.extractor,
            )
        else:
            ck = cache_key(
                content_hash=content_hash,
                schema_fp=schema_fp,
                extraction_mode=cache_mode,
                document_model_id=model_id,
                extractor=settings.extractor,
            )
            content_ck = ck

        cached = await get_cached(ck)
        if cached is None and content_ck != ck:
            cached = await get_cached(content_ck)
        if cached is not None:
            return _cached_result(
                cached,
                read_path_id=read_path.id,
                val_mode=val_mode,
                model_id=model_id,
                document_type=document_type,
                content_hash=content_hash,
                markdown_extraction=markdown_extraction,
            )

        t0 = time.perf_counter()
        bundle_ms = 0
        extract_ms = 0
        async with start_span(
            "extraction.pipeline",
            {
                "path": read_path.id,
                "model": model_id,
                "validation": val_mode,
                "document_type": document_type,
            },
        ):
            tb = time.perf_counter()
            bundle = await asyncio.to_thread(
                load_document_bundle,
                document_bytes,
                mime_type,
                settings=settings,
            )
            bundle_ms = int((time.perf_counter() - tb) * 1000)
            te = time.perf_counter()
            result = await extract_with_document_model(
                model_spec,
                bundle,
                schema,
                document_type,
                extraction_instructions=extraction_instructions,
                markdown_extraction=markdown_extraction,
            )
            extract_ms = int((time.perf_counter() - te) * 1000)
            log.info(
                "document_model_extracted",
                model_id=model_spec.id,
                runtime=model_spec.runtime,
                runtime_model=model_spec.runtime_model,
                ms=extract_ms,
            )

        extraction_ms = int((time.perf_counter() - t0) * 1000)
        used = result.read_path_used or read_path.id
        result.meta = ExtractionMetadata(
            read_path_config=read_path.id,
            read_path_used=used,
            read_path_label=read_path_used_label(used),
            validation_mode=val_mode,
            validation_label=validation_mode_label(val_mode),
            document_model_id=model_id,
            extraction_ms=extraction_ms,
            cache_hit=False,
            gpu_cold_start_likely=gpu_cold_start_likely(extraction_ms),
            fields_extracted=sum(1 for f in result.fields if f.extracted),
            markdown_extraction=markdown_extraction,
            ocr_text=truncate_ocr_text(result.ocr_text) if markdown_extraction else None,
            raw_text=truncate_text(result.raw_text),
            ocr_skipped=result.ocr_skipped,
            pages_rendered=result.pages_rendered,
            pages_sent=result.pages_sent,
            pages_dropped=result.pages_dropped,
        )
        log.info(
            "pipeline_extracted",
            path=read_path.id,
            model=model_id,
            document_type=document_type,
            ms=extraction_ms,
            bundle_ms=bundle_ms,
            extract_ms=extract_ms,
            cache_hit=False,
        )
        await set_cached(ck, result)
        if content_ck != ck:
            await set_cached(content_ck, result)
        return result
