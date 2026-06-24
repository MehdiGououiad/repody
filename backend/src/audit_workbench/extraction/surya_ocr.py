"""Surya OCR 2 adapter — layout-aware OCR for benchmark comparison.

Follows https://huggingface.co/datalab-to/surya-ocr-2: RecognitionPredictor +
SuryaInferenceManager with a pre-running llama-server (datalab-to/surya-ocr-2-gguf).

Optional modes (AUDIT_SURYA_LAYOUT_BLOCK_OCR_ENABLED / AUDIT_SURYA_TABLE_RECOGNITION_ENABLED):
- Layout + block OCR: LayoutPredictor → RecognitionPredictor(..., layouts, full_page=False)
- Table recognition: TableRecPredictor.predict_full appended per page

Document input uses :mod:`document_render` (native images; no platform upscale/downscale).
Inference env uses :mod:`model_inference_env` (Surya-documented variables only).
"""

from __future__ import annotations

import asyncio
import os
import re
from html import unescape
from typing import Any

import structlog

from audit_workbench.extraction.base import ExtractionResult, SchemaFieldSpec, truncate_ocr_text, truncate_text
from audit_workbench.extraction.document_bundle import DocumentBundle
from audit_workbench.extraction.document_render import surya_pil_pages
from audit_workbench.extraction.model_inference_env import surya_inference_env
from audit_workbench.extraction.schema_fields import empty_fields_from_schema
from audit_workbench.settings import Settings, get_settings

log = structlog.get_logger()

_TAG_RE = re.compile(r"<[^>]+>")


def surya_package_installed() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("surya.inference") is not None
    except ImportError:
        return False


def surya_inference_configured(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return bool((settings.surya_inference_url or "").strip())


def _require_surya_inference_url(settings: Settings) -> str:
    url = (settings.surya_inference_url or "").strip().rstrip("/")
    if not url:
        raise RuntimeError(
            "Surya OCR requires a pre-running llama-server. Set AUDIT_SURYA_INFERENCE_URL "
            "(SURYA_INFERENCE_BACKEND=llamacpp), e.g. http://host.docker.internal:8001/v1. "
            "See deploy/llamacpp/README.md#surya-ocr-2."
        )
    return url


def build_surya_env_updates(settings: Settings) -> dict[str, str]:
    """Surya-documented env vars for RecognitionPredictor."""
    return surya_inference_env(settings, inference_url=_require_surya_inference_url(settings))


def _apply_surya_env(settings: Settings) -> dict[str, str | None]:
    previous: dict[str, str | None] = {}
    for key, value in build_surya_env_updates(settings).items():
        previous[key] = os.environ.get(key)
        os.environ[key] = value
    return previous


def _restore_env(previous: dict[str, str | None]) -> None:
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def _block_html(block: Any) -> str:
    if isinstance(block, dict):
        if block.get("skipped"):
            return ""
        return str(block.get("html") or "")
    if getattr(block, "skipped", False):
        return ""
    return str(getattr(block, "html", "") or "")


def _html_to_text(fragment: str) -> str:
    if not fragment:
        return ""
    text = _TAG_RE.sub("\n", fragment)
    text = unescape(text)
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _predictions_to_text(predictions: list[Any]) -> str:
    page_chunks: list[str] = []
    for page_index, page in enumerate(predictions, start=1):
        blocks = page.get("blocks") if isinstance(page, dict) else getattr(page, "blocks", None)
        if not blocks:
            continue
        block_texts = [_html_to_text(_block_html(block)) for block in blocks]
        joined = "\n".join(text for text in block_texts if text)
        if joined:
            page_chunks.append(f"## Page {page_index}\n\n{joined}")
    return "\n\n".join(page_chunks).strip()


def _table_results_to_text(table_results: list[Any]) -> str:
    page_chunks: list[str] = []
    for page_index, result in enumerate(table_results, start=1):
        if isinstance(result, dict):
            error = bool(result.get("error"))
            html = result.get("html")
            rows = result.get("rows") or []
            cols = result.get("cols") or []
        else:
            error = bool(getattr(result, "error", False))
            html = getattr(result, "html", None)
            rows = getattr(result, "rows", None) or []
            cols = getattr(result, "cols", None) or []

        if error:
            continue
        if html:
            text = _html_to_text(str(html))
            if text:
                page_chunks.append(f"## Page {page_index} (tables)\n\n{text}")
            continue
        if rows or cols:
            page_chunks.append(
                f"## Page {page_index} (tables)\n\n"
                f"{len(rows)} row(s) × {len(cols)} column(s) detected"
            )
    return "\n\n".join(page_chunks).strip()


def _run_surya_pipeline(page_images: list[Any], settings: Settings) -> str:
    env_backup = _apply_surya_env(settings)
    try:
        from surya.inference import SuryaInferenceManager
        from surya.recognition import RecognitionPredictor

        manager = SuryaInferenceManager()
        recognition = RecognitionPredictor(manager)

        if settings.surya_layout_block_ocr_enabled:
            from surya.layout import LayoutPredictor

            layouts = LayoutPredictor(manager)(page_images)
            ocr_predictions = recognition(page_images, layouts, full_page=False)
        else:
            ocr_predictions = recognition(page_images)

        sections = [_predictions_to_text(ocr_predictions)]

        if settings.surya_table_recognition_enabled:
            from surya.table_rec import TableRecPredictor

            table_results = TableRecPredictor(manager).predict_full(page_images)
            table_text = _table_results_to_text(table_results)
            if table_text:
                sections.append(table_text)

        return "\n\n".join(section for section in sections if section).strip()
    finally:
        _restore_env(env_backup)


async def extract_with_surya_ocr2(
    bundle: DocumentBundle,
    schema: list[SchemaFieldSpec],
    document_type: str,
    *,
    markdown_extraction: bool = False,
) -> ExtractionResult:
    if not surya_package_installed():
        raise RuntimeError(
            "Surya OCR is not installed. Rebuild the worker image with BACKEND_EXTRAS=otel,ocr."
        )

    settings = get_settings()
    _require_surya_inference_url(settings)

    page_images = surya_pil_pages(bundle, settings)
    if not page_images:
        raise RuntimeError("Document produced no renderable pages for Surya OCR.")

    log.info(
        "surya_ocr_start",
        document_type=document_type,
        pages=len(page_images),
        inference_url=settings.surya_inference_url,
        image_dpi=settings.surya_image_dpi,
        layout_block_ocr=settings.surya_layout_block_ocr_enabled,
        table_recognition=settings.surya_table_recognition_enabled,
    )
    raw_text = truncate_text(
        await asyncio.to_thread(_run_surya_pipeline, page_images, settings),
    )
    if not raw_text:
        raise RuntimeError("Surya OCR returned no text for the document.")

    if markdown_extraction:
        return ExtractionResult(
            fields=empty_fields_from_schema(schema),
            ocr_text=truncate_ocr_text(raw_text),
            read_path_used="document_model",
        )

    return ExtractionResult(
        fields=empty_fields_from_schema(schema),
        raw_text=raw_text,
        read_path_used="document_model",
    )
