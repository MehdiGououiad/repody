"""OpenAPI schemas for the models catalog."""

from __future__ import annotations

from repody.schemas.common import CamelModel


class CatalogModelEntry(CamelModel):
    id: str
    label: str
    description: str = ""
    served_model: str = ""
    available: bool = True
    availability_note: str | None = None


class ModelsCatalogResponse(CamelModel):
    models: list[CatalogModelEntry]
