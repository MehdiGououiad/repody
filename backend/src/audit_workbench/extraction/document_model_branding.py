"""Public document-model branding (user-visible catalog id and labels)."""

from __future__ import annotations

REPODY_VLM_CATALOG_ID = "repody:vlm"
REPODY_VLM_LABEL = "Repody VLM"
REPODY_VLM_DESCRIPTION = (
    "Repody VLM extracts structured fields from document images using your workflow schema."
)

DEFAULT_DOCUMENT_MODEL_CATALOG_ID = REPODY_VLM_CATALOG_ID


def is_legacy_catalog_id(model_id: str | None) -> bool:
    """True when the id is not the canonical Repody VLM catalog id."""
    if not model_id:
        return False
    return model_id.strip() != REPODY_VLM_CATALOG_ID


def normalize_public_catalog_id(model_id: str | None) -> str:
    if not model_id:
        return REPODY_VLM_CATALOG_ID
    stripped = model_id.strip()
    if stripped == REPODY_VLM_CATALOG_ID:
        return REPODY_VLM_CATALOG_ID
    return REPODY_VLM_CATALOG_ID


def public_runtime_model_name(_runtime_model: str) -> str:
    """Hide underlying served model names from API/UI consumers."""
    return REPODY_VLM_LABEL


def public_runtime_name(runtime: str) -> str:
    if runtime in ("docker_model_runner", "vllm"):
        return REPODY_VLM_LABEL
    return runtime


def public_document_model_label(model_id: str | None) -> str:
    """User-visible model name (hides legacy catalog ids and served model names)."""
    if not model_id or is_legacy_catalog_id(model_id) or model_id == REPODY_VLM_CATALOG_ID:
        return REPODY_VLM_LABEL
    return model_id
