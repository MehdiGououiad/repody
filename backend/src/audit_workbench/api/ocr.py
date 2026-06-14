from __future__ import annotations

from fastapi import APIRouter
from pydantic import Field

from audit_workbench.extraction.document_model_branding import public_runtime_name
from audit_workbench.schemas.common import CamelModel
from audit_workbench.services.document_model_catalog import list_catalog_with_availability

router = APIRouter(tags=["ocr"])


class OcrModelOption(CamelModel):
    id: str
    label: str
    engine: str
    runtime: str
    description: str = ""
    available: bool = True
    availability_note: str | None = Field(
        default=None,
        serialization_alias="availabilityNote",
    )
    is_default: bool = Field(default=False, serialization_alias="isDefault")


class OcrModelsResponse(CamelModel):
    models: list[OcrModelOption]
    default_model: str = Field(serialization_alias="defaultModel")


@router.get("/ocr/models", response_model=OcrModelsResponse)
async def list_ocr_models() -> OcrModelsResponse:
    entries, default = await list_catalog_with_availability()
    models = [
        OcrModelOption(
            id=entry.spec.id,
            label=entry.spec.label,
            engine=entry.spec.engine,
            runtime=public_runtime_name(entry.spec.runtime),
            description=entry.spec.description,
            available=entry.available,
            availability_note=entry.availability_note,
            is_default=entry.spec.id == default,
        )
        for entry in entries
    ]
    return OcrModelsResponse(models=models, default_model=default)
