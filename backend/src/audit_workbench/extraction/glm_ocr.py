"""GLM-OCR markdown adapter — official zai-org GlmOcr SDK only.

Document parsing (recommended by the model card):
  https://huggingface.co/zai-org/GLM-OCR

  GlmOcr(mode="selfhosted")
    → PP-DocLayoutV3 layout
    → region OCR via llama-server (ggml-org/GLM-OCR-GGUF)
    → Text / Table / Formula Recognition prompts from glmocr/config.yaml

Install: ``uv sync --extra glmocr`` (workers: ``REPODY_BACKEND_EXTRAS=otel,glmocr``).
"""

from __future__ import annotations

import asyncio
import time

import structlog

from audit_workbench.catalog.adapters import register_document_model_adapter
from audit_workbench.catalog.registry import DocumentModelSpec
from audit_workbench.extraction.branding import GLM_OCR_CATALOG_ID
from audit_workbench.extraction.glm_ocr_sdk import (
    DEFAULT_LAYOUT_MODEL,
    GlmOcrSdkSettings,
    parse_markdown,
    sdk_importable,
)
from audit_workbench.extraction.schema import empty_fields_from_schema
from audit_workbench.extraction.types import (
    DocumentBundle,
    ExtractionIclExample,
    ExtractionResult,
    SchemaFieldSpec,
    truncate_text,
)
from audit_workbench.settings import get_settings

log = structlog.get_logger()


def _require_sdk() -> None:
    if sdk_importable():
        return
    raise RuntimeError(
        "GLM-OCR requires the official glmocr SDK (PP-DocLayoutV3) in the extract "
        "worker image. Rebuild with REPODY_BACKEND_EXTRAS=otel,glmocr "
        "(Compose / pnpm images:build default), or for host tests: "
        "uv sync --extra glmocr. Docs: https://huggingface.co/zai-org/GLM-OCR"
    )


def _pdf_page_count(document_bytes: bytes, mime_type: str) -> int | None:
    """Cheap page count for telemetry when the payload is a PDF."""
    mime = (mime_type or "").split(";", 1)[0].strip().lower()
    if mime != "application/pdf" and not document_bytes.startswith(b"%PDF"):
        return None
    try:
        import fitz
    except ImportError:
        return None
    try:
        with fitz.open(stream=document_bytes, filetype="pdf") as doc:
            return int(doc.page_count)
    except Exception:  # noqa: BLE001 — telemetry only
        return None


async def extract_with_glm_ocr(
    bundle: DocumentBundle,
    schema: list[SchemaFieldSpec],
    document_type: str,
    *,
    spec: DocumentModelSpec | None = None,
    extraction_instructions: str = "",
    markdown_extraction: bool = False,
    extraction_icl_examples: list[ExtractionIclExample] | None = None,
) -> ExtractionResult:
    """Markdown-only extraction via official GlmOcr selfhosted SDK."""
    _ = document_type
    _ = extraction_instructions
    _ = extraction_icl_examples
    _ = markdown_extraction
    _require_sdk()

    settings = get_settings()
    catalog_id = spec.id if spec else GLM_OCR_CATALOG_ID
    base = (settings.glm_ocr_base_url or "").rstrip("/")
    if not base:
        raise RuntimeError(
            "GLM-OCR base URL is empty. Set AUDIT_GLM_OCR_BASE_URL "
            "(example: http://127.0.0.1:8083/v1 after `pnpm glmocr:serve`)."
        )

    pdf_max = settings.glm_ocr_pdf_max_pages
    page_count = _pdf_page_count(bundle.raw_bytes, bundle.mime_type)
    pages_sent = page_count
    pages_dropped = 0
    if page_count is not None and pdf_max is not None and page_count > pdf_max:
        pages_sent = pdf_max
        pages_dropped = page_count - pdf_max

    cfg = GlmOcrSdkSettings(
        base_url=base,
        model=(settings.glm_ocr_served_model or "GLM-OCR").strip(),
        timeout_seconds=int(settings.glm_ocr_timeout_seconds),
        layout_device=(settings.glm_ocr_layout_device or "cpu").strip() or "cpu",
        layout_model_dir=(settings.glm_ocr_layout_model_dir or "").strip()
        or DEFAULT_LAYOUT_MODEL,
        max_workers=int(settings.glm_ocr_sdk_max_workers),
        pdf_max_pages=pdf_max,
    )
    started = time.perf_counter()
    markdown = await asyncio.to_thread(
        parse_markdown,
        bundle.raw_bytes,
        cfg=cfg,
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    log.info(
        "glm_ocr_sdk_done",
        catalog_id=catalog_id,
        runtime="glm_ocr",
        pipeline="sdk",
        markdown_chars=len(markdown),
        elapsed_ms=elapsed_ms,
        base_url=base,
        model=cfg.model,
        layout_device=cfg.layout_device,
        pages_total=page_count,
        pages_sent=pages_sent,
        pages_dropped=pages_dropped,
        pdf_max_pages=pdf_max,
    )
    return ExtractionResult(
        fields=empty_fields_from_schema(schema),
        raw_text=None,
        markdown_text=truncate_text(markdown),
        pages_rendered=page_count,
        pages_sent=pages_sent,
        pages_dropped=pages_dropped if pages_dropped else None,
    )


register_document_model_adapter(GLM_OCR_CATALOG_ID, extract_with_glm_ocr)
