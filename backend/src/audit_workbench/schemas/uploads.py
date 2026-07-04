"""Upload API schemas."""

from __future__ import annotations

from pydantic import Field

from audit_workbench.schemas.common import CamelModel


class UploadItem(CamelModel):
    id: str
    storage_key: str
    file_name: str
    mime_type: str
    size: int


class UploadResponse(CamelModel):
    uploads: list[UploadItem]


class PresignFileRequest(CamelModel):
    file_name: str
    mime_type: str
    size: int = Field(ge=1)
    document_id: str | None = None


class PresignRequest(CamelModel):
    files: list[PresignFileRequest]


class PresignedUploadItem(CamelModel):
    id: str
    storage_key: str
    file_name: str
    mime_type: str
    size: int
    document_id: str | None = None
    upload_url: str | None = None
    method: str = "PUT"
    headers: dict[str, str] = Field(default_factory=dict)


class PresignResponse(CamelModel):
    upload_mode: str = Field(description="presigned | api")
    uploads: list[PresignedUploadItem]


class ConfirmUploadRequest(CamelModel):
    storage_keys: list[str]


class ConfirmUploadItem(CamelModel):
    storage_key: str
    file_name: str
    mime_type: str
    size: int


class ConfirmUploadResponse(CamelModel):
    uploads: list[ConfirmUploadItem]


class UploadCapabilitiesResponse(CamelModel):
    storage_backend: str = Field(serialization_alias="storageBackend")
    direct_upload_enabled: bool = Field(serialization_alias="directUploadEnabled")
    upload_mode: str = Field(serialization_alias="uploadMode")
    max_upload_bytes: int = Field(serialization_alias="maxUploadBytes")
    max_upload_files: int = Field(serialization_alias="maxUploadFiles")
