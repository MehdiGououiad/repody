"""PP-OCRv6 + Qwen structured extraction — official OCR then text LLM → JSON.

Stage 1: PaddleX Basic Serving ``POST /ocr`` (same as ``paddleocr:v6``).
Stage 2: shared OCR→Qwen pipeline in ``extraction.ocr_qwen``.

Requires both services:
  pnpm paddleocr:v6:serve   (:8868)
  pnpm qwen35:serve         (:8084)
"""

from __future__ import annotations

from repody.catalog.adapters import register_document_model_adapter
from repody.catalog.registry import DocumentModelSpec
from repody.extraction.branding import PADDLEOCR_QWEN_CATALOG_ID
from repody.extraction.ocr_qwen import OcrPages, extract_via_ocr_then_qwen
from repody.extraction.paddleocr_v6 import fetch_paddleocr_markdown
from repody.extraction.types import (
    DocumentBundle,
    ExtractionIclExample,
    ExtractionResult,
    SchemaFieldSpec,
)
from repody.settings import get_settings


async def extract_with_paddleocr_qwen(
    bundle: DocumentBundle,
    schema: list[SchemaFieldSpec],
    document_type: str,
    *,
    spec: DocumentModelSpec | None = None,
    extraction_instructions: str = "",
    markdown_extraction: bool = False,
    extraction_icl_examples: list[ExtractionIclExample] | None = None,
) -> ExtractionResult:
    """Structured extraction: PP-OCRv6 markdown → Qwen JSON."""
    # In-context examples steer the vision path only; the text LLM ignores them.
    _ = extraction_icl_examples

    async def run_ocr() -> OcrPages:
        markdown, page_count = await fetch_paddleocr_markdown(bundle)
        # PaddleX rasterises every page it is given, so nothing is ever dropped.
        return OcrPages(markdown=markdown, rendered=page_count, sent=page_count, dropped=0)

    return await extract_via_ocr_then_qwen(
        schema,
        document_type,
        run_ocr=run_ocr,
        runtime="paddleocr_qwen",
        catalog_id=(spec.id if spec else PADDLEOCR_QWEN_CATALOG_ID),
        ocr_base_url=(get_settings().paddleocr_v6_base_url or "").rstrip("/"),
        extraction_instructions=extraction_instructions,
        markdown_extraction=markdown_extraction,
    )


register_document_model_adapter(PADDLEOCR_QWEN_CATALOG_ID, extract_with_paddleocr_qwen)
