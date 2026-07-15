"""Catalog API assembly for platform endpoints."""

from __future__ import annotations

from audit_workbench.catalog.probes import list_catalog_with_availability
from audit_workbench.catalog.registry import list_document_models
from audit_workbench.extraction.document_model_branding import (
    public_runtime_model_name,
    public_runtime_name,
)
from audit_workbench.extraction.document_modes import list_read_paths, list_validation_modes
from audit_workbench.schemas.models_catalog import (
    CatalogModelEntry,
    ModelsCatalogResponse,
    ReadPathOption,
    ValidationModeOption,
)
from audit_workbench.settings import Settings, get_settings


def document_model_summaries() -> list[dict[str, str]]:
    """Public document model rows for platform config and diagnostics."""
    return [
        {
            "id": spec.id,
            "label": spec.label,
            "runtime": public_runtime_name(spec.runtime),
            "runtime_model": public_runtime_model_name(spec.runtime_model),
        }
        for spec in list_document_models()
    ]


def build_processing_paths(
    settings: Settings | None = None,
) -> tuple[list[ReadPathOption], list[ValidationModeOption], str, str]:
    settings = settings or get_settings()
    paths = [
        ReadPathOption(
            id=p.id,
            label=p.label,
            description=p.description,
            read_kind=p.read,
            show_document_model=p.show_document_model,
        )
        for p in list_read_paths()
    ]
    validation_modes = [
        ValidationModeOption(id=v.id, label=v.label, description=v.description)
        for v in list_validation_modes(settings)
    ]
    return paths, validation_modes, "document_model", "logic_only"


async def fetch_models_catalog() -> ModelsCatalogResponse:
    settings = get_settings()
    entries, default_doc = await list_catalog_with_availability()
    paths, validation_modes, default_path, default_validation_mode = build_processing_paths(settings)
    models: list[CatalogModelEntry] = []

    for entry in entries:
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
                markdown_only=entry.spec.markdown_only,
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
                runtime=public_runtime_name("llamacpp"),
                available=True,
                is_default=True,
            )
        )

    return ModelsCatalogResponse(
        models=models,
        default_document_model=default_doc,
        default_validation_model=default_validation,
        inference_mode=settings.inference_mode,
        paths=paths,
        validation_modes=validation_modes,
        default_path=default_path,
        default_validation_mode=default_validation_mode,
    )
