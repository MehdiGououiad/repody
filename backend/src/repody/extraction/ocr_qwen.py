"""Shared two-stage pipeline: OCR to markdown, then Qwen text-to-JSON.

`glm:ocr:qwen` and `paddleocr:qwen` differ only in which OCR engine produces
the markdown. Everything after that — the empty-schema short circuit, Qwen
configuration checks, timing, logging and result shape — lives here so the two
adapters stay honest about being one algorithm with two front ends.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import structlog

from repody.extraction.qwen_text import extract_fields_from_text
from repody.extraction.schema import empty_fields_from_schema
from repody.extraction.types import (
    ExtractionResult,
    SchemaFieldSpec,
    truncate_text,
)
from repody.settings import get_settings

log = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class OcrPages:
    """Markdown produced by an OCR stage, plus its page accounting."""

    markdown: str
    rendered: int | None
    sent: int | None
    dropped: int | None


OcrStage = Callable[[], Awaitable[OcrPages]]


def _qwen_endpoint() -> tuple[str, str]:
    """Resolve the Qwen base URL and model id, failing loudly when unset."""
    settings = get_settings()
    base_url = (settings.qwen35_base_url or "").rstrip("/")
    if not base_url:
        raise RuntimeError(
            "Qwen base URL is empty. Set AUDIT_QWEN35_BASE_URL "
            "(example: http://127.0.0.1:8084/v1 after `pnpm qwen35:serve`)."
        )
    model = (settings.qwen35_served_model or "").strip()
    if not model:
        raise RuntimeError(
            "Qwen model id is empty. Set AUDIT_QWEN35_SERVED_MODEL (default Qwen3.5-4B)."
        )
    return base_url, model


async def extract_via_ocr_then_qwen(
    schema: list[SchemaFieldSpec],
    document_type: str,
    *,
    run_ocr: OcrStage,
    runtime: str,
    catalog_id: str,
    ocr_base_url: str,
    extraction_instructions: str = "",
    markdown_extraction: bool = False,
) -> ExtractionResult:
    """Run the OCR stage, then map its markdown onto the UI schema with Qwen."""
    settings = get_settings()
    has_schema = any(field.name.strip() for field in schema)

    ocr_started = time.perf_counter()
    pages = await run_ocr()
    ocr_ms = int((time.perf_counter() - ocr_started) * 1000)

    # Markdown-only runs have no fields to fill, so the LLM stage is skipped.
    if not has_schema:
        return ExtractionResult(
            fields=empty_fields_from_schema(schema),
            markdown_text=truncate_text(pages.markdown) if markdown_extraction else None,
            pages_rendered=pages.rendered,
            pages_sent=pages.sent,
            pages_dropped=pages.dropped,
        )

    qwen_base, model = _qwen_endpoint()

    llm_started = time.perf_counter()
    fields, raw_json = await extract_fields_from_text(
        base_url=qwen_base,
        model=model,
        schema=schema,
        ocr_text=pages.markdown,
        document_type=document_type,
        extraction_instructions=extraction_instructions,
        timeout=float(settings.qwen35_timeout_seconds),
    )
    llm_ms = int((time.perf_counter() - llm_started) * 1000)

    done_event = f"{runtime}_done"
    log.info(
        done_event,
        catalog_id=catalog_id,
        runtime=runtime,
        pages=pages.rendered or 1,
        markdown_chars=len(pages.markdown),
        ocr_ms=ocr_ms,
        llm_ms=llm_ms,
        extracted=sum(1 for field in fields if field.extracted),
        ocr_base_url=ocr_base_url,
        qwen_base_url=qwen_base,
    )
    return ExtractionResult(
        fields=fields,
        raw_text=raw_json,
        markdown_text=truncate_text(pages.markdown),
        pages_rendered=pages.rendered,
        pages_sent=pages.sent,
        pages_dropped=pages.dropped,
    )
