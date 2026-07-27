"""Document extraction pipeline — cache-aware functional entrypoint."""

from __future__ import annotations

import asyncio
import hashlib
import time
from collections.abc import Awaitable, Callable
from functools import lru_cache

import structlog

from audit_workbench.catalog.registry import (
    extract_with_document_model,
    is_markdown_only_model,
    normalize_model_id,
    parse_document_model,
)
import audit_workbench.extraction.vlm  # noqa: F401 — register catalog adapters
import audit_workbench.extraction.paddleocr_v6  # noqa: F401 — register paddleocr:v6
import audit_workbench.extraction.glm_ocr  # noqa: F401 — register glm:ocr
from audit_workbench.extraction.types import (
    ExtractionIclExample,
    ExtractionMetadata,
    ExtractionResult,
    SchemaFieldSpec,
    load_document_bundle,
    truncate_markdown_text,
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
from audit_workbench.extraction.modes import (
    LOGIC_VALIDATION,
    parse_read_path,
    read_path_used_label,
    resolve_read_path_for_document,
    validation_mode_label,
    gpu_cold_start_likely,
)
from audit_workbench.extraction.nuextract import extraction_inference_profile_key
from audit_workbench.extraction.schema import empty_fields_from_schema, fields_from_sample_values
from audit_workbench.observability.tracing import start_span
from audit_workbench.settings import get_settings
from audit_workbench.util.json_shape import normalize_keys_to_snake

log = structlog.get_logger()

ExtractDocumentFn = Callable[..., Awaitable[ExtractionResult]]


def extract_document_fields(
    schema: list[dict],
    *,
    sample_values: dict[str, str] | None = None,
) -> list:
    """Sync helper for dry-run callers — never injects hardcoded demo data."""
    specs = [
        SchemaFieldSpec(
            name=(row.get("name") or "").strip(),
            description=row.get("description") or "",
            template_type=row.get("template_type"),
        )
        for f in schema
        for row in [normalize_keys_to_snake(f) if isinstance(f, dict) else f]
        if isinstance(row, dict) and (row.get("name") or "").strip()
    ]
    if sample_values:
        return fields_from_sample_values(specs, sample_values)
    return empty_fields_from_schema(specs)


async def stub_extract_document(
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
    validation_mode: str = "logic_only",
    extraction_instructions: str = "",
    markdown_extraction: bool = False,
    extraction_icl_examples: list[ExtractionIclExample] | None = None,
) -> ExtractionResult:
    _ = (
        document_bytes,
        mime_type,
        document_type,
        extraction_mode,
        document_model_id,
        storage_key,
        file_size,
        bundle,
        validation_mode,
        extraction_instructions,
        markdown_extraction,
        extraction_icl_examples,
    )
    return ExtractionResult(fields=empty_fields_from_schema(schema))


def _icl_fingerprint(examples: list[ExtractionIclExample] | None) -> str:
    if not examples:
        return "0"
    parts = [f"{ex.input.strip()}\x1f{ex.output.strip()}" for ex in examples if ex.input.strip()]
    if not parts:
        return "0"
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:8]


def _store_markdown_text(
    text: str | None,
    *,
    model_id: str,
    markdown_extraction: bool,
) -> str | None:
    """Persist markdown for UI/cache.

    NuExtract markdown may include HTML tables/figures → normalize for preview.
    Pure OCR adapters (Paddle / GLM) stay verbatim so post-process
    cannot alter recognition accuracy.
    """
    if not markdown_extraction:
        return None
    if is_markdown_only_model(model_id):
        return truncate_text(text)
    return truncate_markdown_text(text)


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
        markdown_text=_store_markdown_text(
            cached.markdown_text,
            model_id=model_id,
            markdown_extraction=markdown_extraction,
        ),
        raw_text=truncate_text(cached.raw_text),
    )
    return cached


async def extract_document(
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
    extraction_icl_examples: list[ExtractionIclExample] | None = None,
) -> ExtractionResult:
    """Cache-aware extraction through the document model registry."""
    _ = bundle
    read_path_config = parse_read_path(extraction_mode)
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

    settings = get_settings()
    model_id = normalize_model_id(document_model_id or settings.default_document_model_id)
    model_spec = parse_document_model(model_id)
    read_path, read_path_used = resolve_read_path_for_document(extraction_mode)
    if read_path.read == "document_model" and model_spec.read_path_id != read_path.id:
        read_path = parse_read_path(model_spec.read_path_id)
        read_path_used = read_path.id
    has_schema_fields = any(field.name.strip() for field in schema)
    if not has_schema_fields and not markdown_extraction:
        return ExtractionResult(
            fields=empty_fields_from_schema(schema),
            raw_text=None,
        )
    cache_profile = extraction_inference_profile_key(settings=settings)
    cache_mode = (
        f"cfg:{read_path_config.id}:used:{read_path_used}:val:{val_mode}:md:{'1' if markdown_extraction else '0'}"
        f":{cache_profile}"
        f":ins:{hashlib.sha256(extraction_instructions.encode()).hexdigest()[:8]}"
        f":icl:{_icl_fingerprint(extraction_icl_examples)}"
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
            read_path_id=read_path_config.id,
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
        loaded = await asyncio.to_thread(
            load_document_bundle,
            document_bytes,
            mime_type,
            settings=settings,
        )
        bundle_ms = int((time.perf_counter() - tb) * 1000)
        te = time.perf_counter()
        result = await extract_with_document_model(
            model_spec,
            loaded,
            schema,
            document_type,
            extraction_instructions=extraction_instructions,
            markdown_extraction=markdown_extraction,
            extraction_icl_examples=extraction_icl_examples,
        )
        log.info(
            "document_model_extracted",
            model_id=model_spec.id,
            runtime=model_spec.runtime,
            runtime_model=model_spec.runtime_model,
            ms=int((time.perf_counter() - te) * 1000),
        )
        extract_ms = int((time.perf_counter() - te) * 1000)

    extraction_ms = int((time.perf_counter() - t0) * 1000)
    used = result.read_path_used or read_path_used
    result.meta = ExtractionMetadata(
        read_path_config=read_path_config.id,
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
        markdown_text=_store_markdown_text(
            result.markdown_text,
            model_id=model_id,
            markdown_extraction=markdown_extraction,
        ),
        raw_text=truncate_text(result.raw_text),
        pages_rendered=result.pages_rendered,
        pages_sent=result.pages_sent,
        pages_dropped=result.pages_dropped,
    )
    log.info(
        "pipeline_extracted",
        path=read_path_config.id,
        path_used=used,
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


@lru_cache
def get_extract_document() -> ExtractDocumentFn:
    """Return the active extract function (stub or full pipeline)."""
    if get_settings().extractor.lower() == "stub":
        return stub_extract_document
    return extract_document
