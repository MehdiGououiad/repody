"""Models catalog for the workflow builder: the one document model plus its live status."""

from __future__ import annotations

from repody.catalog.registry import list_document_models
from repody.catalog.status import model_status
from repody.extraction.branding import REPODY_VLM_CATALOG_ID, public_runtime_name
from repody.extraction.modes import list_read_paths, list_validation_modes
from repody.schemas.models_catalog import (
    CatalogModelEntry,
    ModelsCatalogResponse,
    ReadPathOption,
    ValidationModeOption,
)
from repody.settings import get_settings


def document_model_summaries() -> list[dict[str, str]]:
    """Public document model rows for platform config."""
    return [
        {
            "id": spec.id,
            "label": spec.label,
            "runtime": public_runtime_name(spec.runtime),
            "runtime_model": spec.label,
        }
        for spec in list_document_models()
    ]


async def fetch_models_catalog() -> ModelsCatalogResponse:
    settings = get_settings()
    status = await model_status(settings)
    note = None
    if not status.reachable:
        note = "llama-server is not reachable — start it with `pnpm llamacpp:serve`."
    elif not status.loaded:
        note = f"llama-server does not serve {settings.llamacpp_served_model!r}."
    models = [
        CatalogModelEntry(
            id=spec.id,
            label=spec.label,
            kind="document_model",
            engine=spec.engine,
            runtime=public_runtime_name(spec.runtime),
            description=spec.description,
            available=status.loaded,
            availability_note=note,
            is_default=True,
        )
        for spec in list_document_models()
    ]
    return ModelsCatalogResponse(
        models=models,
        default_document_model=REPODY_VLM_CATALOG_ID,
        inference_mode=settings.inference_mode,
        paths=[
            ReadPathOption(
                id=p.id,
                label=p.label,
                description=p.description,
                read_kind=p.read,
                show_document_model=p.show_document_model,
            )
            for p in list_read_paths()
        ],
        validation_modes=[
            ValidationModeOption(id=v.id, label=v.label, description=v.description)
            for v in list_validation_modes()
        ],
    )
