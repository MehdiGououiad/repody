"""GLM-OCR + Qwen structured extraction — official SDK markdown then text LLM → JSON.

Stage 1: official GlmOcr SDK (PP-DocLayoutV3 + GLM-OCR region OCR) — same as ``glm:ocr``.
Stage 2: shared OCR→Qwen pipeline in ``extraction.ocr_qwen``.

Requires:
  pnpm glmocr:serve    (:8083)
  pnpm qwen35:serve    (:8084)
  worker extras otel,glmocr
"""

from __future__ import annotations

from repody.catalog.adapters import register_document_model_adapter
from repody.catalog.registry import DocumentModelSpec
from repody.extraction.branding import GLM_OCR_QWEN_CATALOG_ID
from repody.extraction.glm_ocr import fetch_glm_ocr_markdown
from repody.extraction.ocr_qwen import OcrPages, extract_via_ocr_then_qwen
from repody.extraction.types import (
    DocumentBundle,
    ExtractionIclExample,
    ExtractionResult,
    SchemaFieldSpec,
)
from repody.settings import get_settings


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
    # In-context examples steer the vision path only; the text LLM ignores them.
    _ = extraction_icl_examples

    async def run_ocr() -> OcrPages:
        markdown, rendered, sent, dropped = await fetch_glm_ocr_markdown(bundle)
        return OcrPages(markdown=markdown, rendered=rendered, sent=sent, dropped=dropped or None)

    return await extract_via_ocr_then_qwen(
        schema,
        document_type,
        run_ocr=run_ocr,
        runtime="glm_ocr_qwen",
        catalog_id=(spec.id if spec else GLM_OCR_QWEN_CATALOG_ID),
        ocr_base_url=(get_settings().glm_ocr_base_url or "").rstrip("/"),
        extraction_instructions=extraction_instructions,
        markdown_extraction=markdown_extraction,
    )


register_document_model_adapter(GLM_OCR_QWEN_CATALOG_ID, extract_with_glm_ocr_qwen)
