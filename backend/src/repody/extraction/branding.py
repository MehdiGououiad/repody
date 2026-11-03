"""Public name of the one document model (NuExtract3 on llama-server)."""

from __future__ import annotations

REPODY_VLM_CATALOG_ID = "repody:vlm"
REPODY_VLM_LABEL = "Repody VLM"
REPODY_VLM_DESCRIPTION = (
    "NuExtract3 structured extraction from page images (local llama-server, "
    "OpenAI-compatible). Optional Markdown transcription."
)


def normalize_public_catalog_id(model_id: str | None) -> str:
    """Every stored id (including retired engines) resolves to the one model."""
    _ = model_id
    return REPODY_VLM_CATALOG_ID


def public_runtime_name(runtime: str) -> str:
    _ = runtime
    return REPODY_VLM_LABEL


def public_document_model_label(model_id: str | None) -> str:
    _ = model_id
    return REPODY_VLM_LABEL
