from __future__ import annotations

from pydantic import Field


class StorageSettingsFields:
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "audit-documents"
    minio_secure: bool = False
    minio_public_endpoint: str | None = Field(
        default=None,
        description=(
            "Browser-reachable MinIO host:port for presigned upload URLs (e.g. localhost:9000)."
        ),
    )
    storage_backend: str = Field(default="local", description="local | s3")
    local_storage_path: str = Field(default=".data/storage")

    max_upload_bytes: int = Field(default=25 * 1024 * 1024)
    max_upload_files: int = Field(default=20)
    presigned_upload_ttl_seconds: int = Field(default=3600)
    direct_upload_enabled: bool = Field(default=True)
    upload_allowed_mime_types: list[str] = Field(
        default_factory=lambda: [
            "application/pdf",
            "image/png",
            "image/jpeg",
            "image/webp",
        ],
    )
