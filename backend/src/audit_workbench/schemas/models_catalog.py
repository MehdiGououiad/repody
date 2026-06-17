"""OpenAPI schemas for the unified models catalog."""

from __future__ import annotations

from pydantic import Field

from audit_workbench.schemas.common import CamelModel


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


class ModelsCatalogResponse(CamelModel):
    models: list[CatalogModelEntry]
    default_document_model: str = Field(serialization_alias="defaultDocumentModel")
    default_validation_model: str | None = Field(
        default=None,
        serialization_alias="defaultValidationModel",
    )
    inference_mode: str = Field(serialization_alias="inferenceMode")
    paths: list[ReadPathOption] = Field(default_factory=list)
    validation_modes: list[ValidationModeOption] = Field(
        default_factory=list,
        serialization_alias="validationModes",
    )
    default_path: str = Field(default="document_model", serialization_alias="defaultPath")
    default_validation_mode: str = Field(
        default="logic_only",
        serialization_alias="defaultValidationMode",
    )
