"""Public document-model branding (user-visible catalog id and labels)."""

from __future__ import annotations

REPODY_VLM_CATALOG_ID = "repody:vlm"
REPODY_VLM_LABEL = "Repody VLM"
REPODY_VLM_DESCRIPTION = (
    "Repody VLM extracts structured fields from document images using your workflow schema."
)

REPODY_VLM_CLOUD_CATALOG_ID = "repody:vlm:cloud"
REPODY_VLM_CLOUD_LABEL = "NuExtract Cloud"
REPODY_VLM_CLOUD_DESCRIPTION = (
    "Official NuExtract platform API for structured extraction "
    "(https://nuextract.ai). Requires AUDIT_NUEXTRACT_CLOUD_API_KEY."
)

PADDLEOCR_V6_CATALOG_ID = "paddleocr:v6"
PADDLEOCR_V6_LABEL = "PP-OCRv6"
PADDLEOCR_V6_DESCRIPTION = (
    "PP-OCRv6 via official PaddleX Basic Serving (POST /ocr). "
    "Default models PP-OCRv6_medium_det/rec. Markdown-only — "
    "recognized lines from prunedResult.rec_texts. "
    "Requires AUDIT_PADDLEOCR_V6_BASE_URL (default http://127.0.0.1:8868)."
)

GLM_OCR_CATALOG_ID = "glm:ocr"
GLM_OCR_LABEL = "GLM-OCR"
GLM_OCR_DESCRIPTION = (
    "GLM-OCR (zai-org/GLM-OCR) via llama-server OpenAI chat API "
    "(ggml-org/GLM-OCR-GGUF). Markdown-only document OCR using the official "
    "image + \"Text Recognition:\" prompt. "
    "Requires AUDIT_GLM_OCR_BASE_URL (default http://127.0.0.1:8083/v1)."
)

PUBLIC_CATALOG_IDS = frozenset(
    {
        REPODY_VLM_CATALOG_ID,
        REPODY_VLM_CLOUD_CATALOG_ID,
        PADDLEOCR_V6_CATALOG_ID,
        GLM_OCR_CATALOG_ID,
    }
)


class UnknownCatalogIdError(ValueError):
    """Raised when a document model catalog id is not registered."""


def normalize_public_catalog_id(model_id: str | None) -> str:
    if not model_id or not str(model_id).strip():
        return REPODY_VLM_CATALOG_ID
    stripped = str(model_id).strip()
    if stripped in PUBLIC_CATALOG_IDS:
        return stripped
    raise UnknownCatalogIdError(f"Unknown document model catalog id: {stripped!r}")


def public_runtime_model_name(runtime_model: str) -> str:
    """Hide underlying served model names from API/UI consumers."""
    _ = runtime_model
    return REPODY_VLM_LABEL


def public_runtime_name(runtime: str) -> str:
    if runtime == "llamacpp":
        return REPODY_VLM_LABEL
    if runtime == "nuextract_cloud":
        return REPODY_VLM_CLOUD_LABEL
    if runtime == "paddleocr_v6":
        return PADDLEOCR_V6_LABEL
    if runtime == "glm_ocr":
        return GLM_OCR_LABEL
    return runtime


def public_document_model_label(model_id: str | None) -> str:
    """User-visible model name (hides served model names)."""
    if not model_id:
        return REPODY_VLM_LABEL
    stripped = model_id.strip()
    if stripped == REPODY_VLM_CATALOG_ID:
        return REPODY_VLM_LABEL
    if stripped == REPODY_VLM_CLOUD_CATALOG_ID:
        return REPODY_VLM_CLOUD_LABEL
    if stripped == PADDLEOCR_V6_CATALOG_ID:
        return PADDLEOCR_V6_LABEL
    if stripped == GLM_OCR_CATALOG_ID:
        return GLM_OCR_LABEL
    return stripped
