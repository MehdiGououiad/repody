"""OpenAPI schemas for the unified models catalog."""

from __future__ import annotations

from pydantic import Field

from repody.schemas.common import CamelModel


class CatalogModelEntry(CamelModel):
    id: str
    label: str
    kind: str  # document_model | validation
    engine: str = ""
    runtime: str = ""
    description: str = ""
    available: bool = True
    availability_note: str | None = None
    is_default: bool = False
    markdown_only: bool = False


class ReadPathOption(CamelModel):
    id: str
    label: str
    description: str
    read_kind: str
    show_document_model: bool


class ValidationModeOption(CamelModel):
    id: str
    label: str
    description: str


class ModelsCatalogResponse(CamelModel):
    models: list[CatalogModelEntry]
    default_document_model: str
    default_validation_model: str | None = None
    inference_mode: str
    paths: list[ReadPathOption] = Field(default_factory=list)
    validation_modes: list[ValidationModeOption] = Field(default_factory=list)
    default_path: str = "document_model"
    default_validation_mode: str = "logic_only"
