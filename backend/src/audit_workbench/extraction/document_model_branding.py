"""Public document-model branding (user-visible catalog id and labels)."""

from __future__ import annotations

REPODY_VLM_CATALOG_ID = "repody:vlm"
REPODY_VLM_LABEL = "Repody VLM"
REPODY_VLM_DESCRIPTION = (
    "Repody VLM extracts structured fields from document images using your workflow schema."
)

PUBLIC_CATALOG_IDS = frozenset({REPODY_VLM_CATALOG_ID})


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
    if runtime in ("docker_model_runner", "vllm"):
        return REPODY_VLM_LABEL
    return runtime


def public_document_model_label(model_id: str | None) -> str:
    """User-visible model name (hides served model names)."""
    if not model_id:
        return REPODY_VLM_LABEL
    stripped = model_id.strip()
    if stripped == REPODY_VLM_CATALOG_ID:
        return REPODY_VLM_LABEL
    return stripped
