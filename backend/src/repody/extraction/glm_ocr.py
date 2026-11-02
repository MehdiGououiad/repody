"""GLM-OCR markdown adapter - official zai-org GlmOcr SDK only.

Document parsing (opt-in):
  https://huggingface.co/zai-org/GLM-OCR

  AUDIT_GLM_OCR_LAYOUT_ENABLED=true
     -> GlmOcr(mode="selfhosted") + PP-DocLayoutV3
     -> region OCR via llama-server (ggml-org/GLM-OCR-GGUF)
     -> Text / Table / Formula Recognition prompts from glmocr/config.yaml

Model-only (default, AUDIT_GLM_OCR_LAYOUT_ENABLED=false):
  whole page -> ``Text Recognition:`` (no PP-DocLayoutV3 weights)

Install: ``uv sync --extra glmocr`` (workers: ``REPODY_BACKEND_EXTRAS=otel,glmocr``).
"""

from __future__ import annotations

import asyncio

import structlog

from repody.extraction.glm_ocr_sdk import (
    DEFAULT_LAYOUT_MODEL,
    GlmOcrSdkSettings,
    parse_markdown,
    sdk_importable,
)
from repody.extraction.types import (
    DocumentBundle,
)
from repody.settings import get_settings

log = structlog.get_logger()


def _require_sdk() -> None:
    if sdk_importable():
        return
    raise RuntimeError(
        "GLM-OCR requires the official glmocr SDK in the extract "
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
    except Exception:
        return None


async def fetch_glm_ocr_markdown(
    bundle: DocumentBundle,
) -> tuple[str, int | None, int | None, int]:
    """Official GlmOcr SDK -> ``(markdown, page_count, pages_sent, pages_dropped)``."""
    _require_sdk()
    settings = get_settings()
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
        layout_model_dir=(settings.glm_ocr_layout_model_dir or "").strip() or DEFAULT_LAYOUT_MODEL,
        max_workers=int(settings.glm_ocr_sdk_max_workers),
        pdf_max_pages=pdf_max,
        id_card_profile=bool(settings.glm_ocr_id_card_profile),
        layout_enabled=bool(settings.glm_ocr_layout_enabled),
    )
    markdown = await asyncio.to_thread(
        parse_markdown,
        bundle.raw_bytes,
        cfg=cfg,
    )
    return markdown, page_count, pages_sent, pages_dropped
