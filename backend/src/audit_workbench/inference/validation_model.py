"""Resolve the dedicated text model used for LLM rule validation."""

from __future__ import annotations

from audit_workbench.settings import Settings, get_settings

VALIDATION_MODEL_REQUIRED_MSG = (
    "LLM validation requires AUDIT_VALIDATION_MODEL "
    "(a dedicated text model on the inference endpoint). "
    "Repody VLM is not used for rule validation."
)


def resolve_llm_validation_model(
    explicit: str | None = None,
    *,
    settings: Settings | None = None,
) -> tuple[str | None, str | None]:
    """Return (model_id, error_detail). Never falls back to the extraction model."""
    if explicit and explicit.strip():
        return explicit.strip(), None
    cfg = settings or get_settings()
    if cfg.validation_model and cfg.validation_model.strip():
        return cfg.validation_model.strip(), None
    return None, VALIDATION_MODEL_REQUIRED_MSG
