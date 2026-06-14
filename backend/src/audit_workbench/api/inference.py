from __future__ import annotations

from fastapi import APIRouter
from pydantic import Field

from audit_workbench.extraction.document_model_branding import (
    normalize_public_catalog_id,
    public_runtime_name,
)
from audit_workbench.extraction.model_registry import list_document_models
from audit_workbench.schemas.common import CamelModel
from audit_workbench.settings import get_settings

router = APIRouter(tags=["inference"])


class InferenceModelSchema(CamelModel):
    id: str
    label: str
    kind: str  # document_model | validation
    runtime: str = "docker_model_runner"
    is_default: bool = Field(default=False, serialization_alias="isDefault")


class InferenceModelsResponse(CamelModel):
    models: list[InferenceModelSchema]
    default_document_model: str = Field(serialization_alias="defaultDocumentModel")
    default_validation_model: str | None = Field(
        default=None,
        serialization_alias="defaultValidationModel",
    )
    inference_mode: str = Field(serialization_alias="inferenceMode")


@router.get("/inference/models", response_model=InferenceModelsResponse)
async def list_inference_models() -> InferenceModelsResponse:
    settings = get_settings()
    models = [
        InferenceModelSchema(
            id=spec.id,
            label=spec.label,
            kind="document_model",
            runtime=public_runtime_name(spec.runtime),
            is_default=spec.id == settings.default_ocr_model,
        )
        for spec in list_document_models()
    ]
    if settings.llm_validation_enabled and settings.validation_model:
        models.append(
            InferenceModelSchema(
                id=settings.validation_model,
                label="Validation model",
                kind="validation",
                runtime="docker_model_runner",
            )
        )
    return InferenceModelsResponse(
        models=models,
        default_document_model=normalize_public_catalog_id(settings.default_ocr_model),
        default_validation_model=settings.validation_model,
        inference_mode=settings.inference_mode,
    )
