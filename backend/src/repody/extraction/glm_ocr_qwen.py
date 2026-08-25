"""GLM-OCR + Qwen structured extraction — official SDK markdown then text LLM → JSON.

Stage 1: official GlmOcr SDK (PP-DocLayoutV3 + GLM-OCR region OCR) — same as ``glm:ocr``.
Stage 2: Qwen3.5 (OpenAI-compatible llama-server) text→JSON on OCR markdown
         (same prompt path as ``paddleocr:qwen``).

Requires:
  pnpm glmocr:serve    (:8083)
  pnpm qwen35:serve    (:8084)
  worker extras otel,glmocr
"""

from __future__ import annotations

import time

import structlog

from repody.catalog.adapters import register_document_model_adapter
from repody.catalog.registry import DocumentModelSpec
from repody.extraction.branding import GLM_OCR_QWEN_CATALOG_ID
from repody.extraction.glm_ocr import fetch_glm_ocr_markdown
from repody.extraction.qwen_text import extract_fields_from_text
from repody.extraction.schema import empty_fields_from_schema
from repody.extraction.types import (
    DocumentBundle,
    ExtractionIclExample,
    ExtractionResult,
    SchemaFieldSpec,
    truncate_text,
)
from repody.settings import get_settings

log = structlog.get_logger()


async def extract_with_glm_ocr_qwen(
    bundle: DocumentBundle,
    schema: list[SchemaFieldSpec],
    document_type: str,
    *,
    spec: DocumentModelSpec | None = None,
    extraction_instructions: str = "",
    markdown_extraction: bool = False,
    extraction_icl_examples: list[ExtractionIclExample] | None = None,
) -> ExtractionResult:
    """Structured extraction: GLM-OCR markdown → Qwen JSON (UI schema)."""
    _ = extraction_icl_examples
    settings = get_settings()
    has_schema = any(field.name.strip() for field in schema)

    ocr_started = time.perf_counter()
    markdown, page_count, pages_sent, pages_dropped = await fetch_glm_ocr_markdown(bundle)
    ocr_ms = int((time.perf_counter() - ocr_started) * 1000)

    if not has_schema:
        return ExtractionResult(
            fields=empty_fields_from_schema(schema),
            markdown_text=truncate_text(markdown) if markdown_extraction else None,
            pages_rendered=page_count,
            pages_sent=pages_sent,
            pages_dropped=pages_dropped if pages_dropped else None,
        )

    qwen_base = (settings.qwen35_base_url or "").rstrip("/")
    if not qwen_base:
        raise RuntimeError(
            "Qwen base URL is empty. Set AUDIT_QWEN35_BASE_URL "
            "(example: http://127.0.0.1:8084/v1 after `pnpm qwen35:serve`)."
        )
    model = (settings.qwen35_served_model or "").strip()
    if not model:
        raise RuntimeError(
            "Qwen model id is empty. Set AUDIT_QWEN35_SERVED_MODEL "
            "(default Qwen3.5-4B)."
        )

    llm_started = time.perf_counter()
    fields, raw_json = await extract_fields_from_text(
        base_url=qwen_base,
        model=model,
        schema=schema,
        ocr_text=markdown,
        document_type=document_type,
        extraction_instructions=extraction_instructions,
        timeout=float(settings.qwen35_timeout_seconds),
    )
    llm_ms = int((time.perf_counter() - llm_started) * 1000)

    log.info(
        "glm_ocr_qwen_done",
        catalog_id=(spec.id if spec else GLM_OCR_QWEN_CATALOG_ID),
        runtime="glm_ocr_qwen",
        pages=page_count or 1,
        markdown_chars=len(markdown),
        ocr_ms=ocr_ms,
        llm_ms=llm_ms,
        extracted=sum(1 for field in fields if field.extracted),
        ocr_base_url=(settings.glm_ocr_base_url or "").rstrip("/"),
        qwen_base_url=qwen_base,
    )
    return ExtractionResult(
        fields=fields,
        raw_text=raw_json,
        markdown_text=truncate_text(markdown),
        pages_rendered=page_count,
        pages_sent=pages_sent,
        pages_dropped=pages_dropped if pages_dropped else None,
    )


register_document_model_adapter(GLM_OCR_QWEN_CATALOG_ID, extract_with_glm_ocr_qwen)
