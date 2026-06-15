"""Unified model catalog read interface."""

from __future__ import annotations

from pydantic import Field

from audit_workbench.extraction.document_model_branding import public_runtime_name
from audit_workbench.extraction.model_registry import list_document_models
from audit_workbench.schemas.common import CamelModel
from audit_workbench.services.document_model_catalog import list_catalog_with_availability
from audit_workbench.settings import get_settings


class CatalogModelEntry(CamelModel):
    id: str
    label: str
    kind: str  # document_model | validation
    engine: str = ""
    runtime: str = ""
    description: str = ""
    available: bool = True
    availability_note: str | None = Field(default=None, serialization_alias="availabilityNote")
    is_default: bool = Field(default=False, serialization_alias="isDefault")


class ModelsCatalogResponse(CamelModel):
    models: list[CatalogModelEntry]
    default_document_model: str = Field(serialization_alias="defaultDocumentModel")
    default_validation_model: str | None = Field(
        default=None,
        serialization_alias="defaultValidationModel",
    )
    inference_mode: str = Field(serialization_alias="inferenceMode")


async def build_models_catalog() -> ModelsCatalogResponse:
    settings = get_settings()
    entries, default_doc = await list_catalog_with_availability()
    seen: set[str] = set()
    models: list[CatalogModelEntry] = []

    for entry in entries:
        seen.add(entry.spec.id)
        models.append(
            CatalogModelEntry(
                id=entry.spec.id,
                label=entry.spec.label,
                kind="document_model",
                engine=entry.spec.engine,
                runtime=public_runtime_name(entry.spec.runtime),
                description=entry.spec.description,
                available=entry.available,
                availability_note=entry.availability_note,
                is_default=entry.spec.id == default_doc,
            )
        )

    for spec in list_document_models():
        if spec.id in seen:
            continue
        models.append(
            CatalogModelEntry(
                id=spec.id,
                label=spec.label,
                kind="document_model",
                runtime=public_runtime_name(spec.runtime),
                is_default=spec.id == settings.default_ocr_model,
            )
        )

    default_validation: str | None = None
    if settings.llm_validation_enabled and settings.validation_model:
        default_validation = settings.validation_model
        models.append(
            CatalogModelEntry(
                id=settings.validation_model,
                label=settings.validation_model,
                kind="validation",
                runtime=public_runtime_name("docker_model_runner"),
                available=True,
                is_default=True,
            )
        )

    return ModelsCatalogResponse(
        models=models,
        default_document_model=default_doc,
        default_validation_model=default_validation,
        inference_mode=settings.inference_mode,
    )
