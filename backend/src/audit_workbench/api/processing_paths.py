from __future__ import annotations

from fastapi import APIRouter
from pydantic import Field

from audit_workbench.extraction.processing_paths import list_read_paths, list_validation_modes
from audit_workbench.schemas.common import CamelModel

router = APIRouter(tags=["processing-paths"])


class ReadPathOption(CamelModel):
    id: str
    label: str
    description: str
    read_kind: str = Field(serialization_alias="readKind")
    show_ocr_model: bool = Field(serialization_alias="showOcrModel")
    ocr_engine: str | None = Field(default=None, serialization_alias="ocrEngine")


class ValidationModeOption(CamelModel):
    id: str
    label: str
    description: str


class ProcessingPathsResponse(CamelModel):
    paths: list[ReadPathOption]
    validation_modes: list[ValidationModeOption] = Field(serialization_alias="validationModes")
    default_path: str = Field(serialization_alias="defaultPath")
    default_validation_mode: str = Field(
        default="logic_only",
        serialization_alias="defaultValidationMode",
    )


@router.get("/processing-paths", response_model=ProcessingPathsResponse)
async def get_processing_paths() -> ProcessingPathsResponse:
    paths = [
        ReadPathOption(
            id=p.id,
            label=p.label,
            description=p.description,
            read_kind=p.read,
            show_ocr_model=p.show_ocr_model,
            ocr_engine=p.ocr_engine,
        )
        for p in list_read_paths()
    ]
    validation_modes = [
        ValidationModeOption(id=v.id, label=v.label, description=v.description)
        for v in list_validation_modes()
    ]
    return ProcessingPathsResponse(
        paths=paths,
        validation_modes=validation_modes,
        default_path="document_model",
        default_validation_mode="logic_only",
    )
