"""GLM-OCR markdown adapter — llama-server OpenAI chat client.

Model card (prompts / tasks):
  https://huggingface.co/zai-org/GLM-OCR

GGUF serve (llama.cpp):
  llama-server -hf ggml-org/GLM-OCR-GGUF
  https://huggingface.co/ggml-org/GLM-OCR-GGUF

Document parsing uses the official prompt ``Text Recognition:``
(image first, then text), matching the Transformers example on the model card.
"""

from __future__ import annotations

from audit_workbench.catalog.adapters import register_document_model_adapter
from audit_workbench.catalog.registry import DocumentModelSpec
from audit_workbench.extraction.branding import GLM_OCR_CATALOG_ID
from audit_workbench.extraction.ocr_chat import extract_markdown_via_ocr_chat
from audit_workbench.extraction.render import (
    GLM_OCR_MAX_TOKENS,
    GLM_OCR_REPEAT_PENALTY,
    GLM_OCR_TEMPERATURE,
    GLM_OCR_TEXT_PROMPT,
    GLM_OCR_TOP_K,
    GLM_OCR_TOP_P,
    glm_ocr_pages,
)
from audit_workbench.extraction.types import (
    DocumentBundle,
    ExtractionIclExample,
    ExtractionResult,
    SchemaFieldSpec,
)
from audit_workbench.settings import get_settings


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
    """Markdown-only extraction via GLM-OCR chat/completions."""
    _ = document_type
    _ = extraction_instructions
    _ = extraction_icl_examples
    _ = markdown_extraction
    settings = get_settings()
    base = (settings.glm_ocr_base_url or "").rstrip("/")
    if not base:
        raise RuntimeError(
            "GLM-OCR base URL is empty. Set AUDIT_GLM_OCR_BASE_URL "
            "(example: http://127.0.0.1:8083/v1 after `pnpm glmocr:serve`)."
        )
    model = (settings.glm_ocr_served_model or "GLM-OCR").strip()
    timeout = float(settings.glm_ocr_timeout_seconds)
    pages, total_pages = glm_ocr_pages(bundle)
    catalog_id = spec.id if spec else GLM_OCR_CATALOG_ID
    return await extract_markdown_via_ocr_chat(
        catalog_id=catalog_id,
        runtime="glm_ocr",
        base_url=base,
        model=model,
        timeout=timeout,
        pages=pages,
        total_pages=total_pages,
        schema=schema,
        text_prompt=GLM_OCR_TEXT_PROMPT,
        max_tokens=GLM_OCR_MAX_TOKENS,
        temperature=GLM_OCR_TEMPERATURE,
        top_p=GLM_OCR_TOP_P,
        top_k=GLM_OCR_TOP_K,
        extra={"repeat_penalty": GLM_OCR_REPEAT_PENALTY},
        empty_error=(
            "GLM-OCR returned empty text. Check llama-server on "
            f"{base} (`pnpm glmocr:serve` / ggml-org/GLM-OCR-GGUF) and that "
            "the document is a supported PDF/image."
        ),
        log_event="glm_ocr_done",
    )


register_document_model_adapter(GLM_OCR_CATALOG_ID, extract_with_glm_ocr)
