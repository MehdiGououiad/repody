"""Public document-model branding (user-visible catalog id and labels)."""

from __future__ import annotations

REPODY_VLM_CATALOG_ID = "repody:vlm"
REPODY_VLM_LABEL = "Repody VLM"
REPODY_VLM_DESCRIPTION = (
    "Repody VLM extracts structured fields from document images using your workflow schema."
)

SURYA_OCR2_CATALOG_ID = "surya:ocr2"
SURYA_OCR2_LABEL = "Surya OCR 2"
SURYA_OCR2_DESCRIPTION = (
    "Datalab Surya OCR 2 — layout-aware text via llama-server. Use with document markdown "
    "preview in workflows; structured fields still come from Repody VLM or a follow-up LLM step."
)

PUBLIC_CATALOG_IDS = frozenset({REPODY_VLM_CATALOG_ID, SURYA_OCR2_CATALOG_ID})


def is_legacy_catalog_id(model_id: str | None) -> bool:
    """True for pre-catalog ids that should map to Repody VLM (not other public models)."""
    if not model_id:
        return False
    stripped = model_id.strip()
    if stripped in PUBLIC_CATALOG_IDS:
        return False
    return stripped != REPODY_VLM_CATALOG_ID


def normalize_public_catalog_id(model_id: str | None) -> str:
    if not model_id:
        return REPODY_VLM_CATALOG_ID
    stripped = model_id.strip()
    if stripped in PUBLIC_CATALOG_IDS:
        return stripped
    # Legacy catalog ids and unknown ids map to Repody VLM.
    return REPODY_VLM_CATALOG_ID


def public_runtime_model_name(runtime_model: str) -> str:
    """Hide underlying served model names from API/UI consumers."""
    _ = runtime_model
    return REPODY_VLM_LABEL


def public_runtime_name(runtime: str) -> str:
    if runtime == "surya":
        return SURYA_OCR2_LABEL
    if runtime in ("docker_model_runner", "vllm"):
        return REPODY_VLM_LABEL
    return runtime


def public_document_model_label(model_id: str | None) -> str:
    """User-visible model name (hides legacy catalog ids and served model names)."""
    if not model_id:
        return REPODY_VLM_LABEL
    stripped = model_id.strip()
    if stripped == SURYA_OCR2_CATALOG_ID:
        return SURYA_OCR2_LABEL
    if is_legacy_catalog_id(stripped) or stripped == REPODY_VLM_CATALOG_ID:
        return REPODY_VLM_LABEL
    return stripped
