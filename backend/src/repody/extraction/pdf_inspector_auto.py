"""Automode: Firecrawl pdf-inspector native PDF text, then Qwen JSON or fallback.

When ``native_pdf_auto`` is on and the upload is a PDF, classify + extract with
pdf-inspector. If quality is good enough, run the same Qwen text→JSON path as
``paddleocr:qwen``. Otherwise the caller falls back to the selected document model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

from repody.extraction.ocr_qwen import OcrPages, extract_via_ocr_then_qwen
from repody.extraction.types import ExtractionResult, SchemaFieldSpec
from repody.settings import get_settings

log = structlog.get_logger()

NATIVE_SOURCE = "pdf_inspector"
FALLBACK_SOURCE = "fallback"

try:
    import pdf_inspector as _pdf_inspector
except ImportError:  # optional until worker image is rebuilt
    _pdf_inspector = None


@dataclass(frozen=True, slots=True)
class PdfInspection:
    pdf_type: str
    confidence: float
    page_count: int
    markdown: str | None
    pages_needing_ocr: tuple[int, ...]
    has_encoding_issues: bool
    available: bool
    error: str | None = None


def mime_is_pdf(mime_type: str, raw_bytes: bytes) -> bool:
    mime = (mime_type or "").lower()
    return mime == "application/pdf" or raw_bytes.startswith(b"%PDF")


def inspect_pdf_bytes(raw: bytes) -> PdfInspection:
    """Run pdf-inspector; soft-fail when the package or parse fails."""
    if _pdf_inspector is None:
        return PdfInspection(
            pdf_type="unknown",
            confidence=0.0,
            page_count=0,
            markdown=None,
            pages_needing_ocr=(),
            has_encoding_issues=True,
            available=False,
            error="pdf-inspector not installed",
        )

    try:
        result = _pdf_inspector.process_pdf_bytes(raw)
    except Exception as exc:
        log.warning("pdf_inspector_failed", error=repr(exc))
        return PdfInspection(
            pdf_type="unknown",
            confidence=0.0,
            page_count=0,
            markdown=None,
            pages_needing_ocr=(),
            has_encoding_issues=True,
            available=False,
            error=repr(exc),
        )

    pages = getattr(result, "pages_needing_ocr", None) or []
    return PdfInspection(
        pdf_type=str(getattr(result, "pdf_type", "") or "").strip().lower(),
        confidence=float(getattr(result, "confidence", 0.0) or 0.0),
        page_count=int(getattr(result, "page_count", 0) or 0),
        markdown=getattr(result, "markdown", None),
        pages_needing_ocr=tuple(int(p) for p in pages),
        has_encoding_issues=bool(getattr(result, "has_encoding_issues", False)),
        available=True,
        error=None,
    )


def native_quality_ok(
    inspection: PdfInspection,
    *,
    min_confidence: float | None = None,
    min_chars: int | None = None,
) -> tuple[bool, str]:
    """Return (ok, reason). reason is empty when ok; else a machine-readable code."""
    settings = get_settings()
    conf_floor = (
        float(min_confidence)
        if min_confidence is not None
        else float(settings.pdf_inspector_min_confidence)
    )
    char_floor = int(min_chars) if min_chars is not None else int(settings.pdf_inspector_min_chars)

    if not inspection.available:
        return False, inspection.error or "pdf_inspector_unavailable"
    if inspection.pdf_type != "text_based":
        return False, f"pdf_type:{inspection.pdf_type or 'unknown'}"
    if inspection.confidence < conf_floor:
        return False, "low_confidence"
    if inspection.has_encoding_issues:
        return False, "encoding_issues"
    if inspection.pages_needing_ocr:
        return False, "pages_needing_ocr"
    markdown = (inspection.markdown or "").strip()
    if not markdown:
        return False, "empty_markdown"
    if len(markdown) < char_floor:
        return False, "short_markdown"
    return True, ""


def native_pdf_meta(
    *,
    source: str,
    inspection: PdfInspection | None = None,
    fallback_reason: str | None = None,
) -> dict[str, Any]:
    """Wire shape nested under extraction_meta.nativePdf."""
    out: dict[str, Any] = {"source": source}
    if inspection is not None:
        out["pdfType"] = inspection.pdf_type
        out["confidence"] = inspection.confidence
        out["pageCount"] = inspection.page_count
    if fallback_reason:
        out["fallbackReason"] = fallback_reason
    return out


async def extract_via_native_markdown(
    *,
    markdown: str,
    schema: list[SchemaFieldSpec],
    document_type: str,
    extraction_instructions: str = "",
    markdown_extraction: bool = False,
    page_count: int = 0,
) -> ExtractionResult:
    """Structured extraction: native markdown → Qwen JSON (same path as paddleocr:qwen)."""
    pages = page_count or 1

    async def native_markdown() -> OcrPages:
        return OcrPages(markdown=markdown, rendered=pages, sent=pages, dropped=0)

    return await extract_via_ocr_then_qwen(
        schema,
        document_type,
        run_ocr=native_markdown,
        runtime="pdf_inspector_qwen",
        catalog_id=NATIVE_SOURCE,
        ocr_base_url="",
        extraction_instructions=extraction_instructions,
        markdown_extraction=markdown_extraction,
    )
