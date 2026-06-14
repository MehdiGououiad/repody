from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from audit_workbench.settings import Settings, get_settings
from audit_workbench.storage.base import ObjectStorage
from audit_workbench.storage.local import LocalObjectStorage
from audit_workbench.storage.s3 import S3ObjectStorage


@lru_cache
def get_storage() -> ObjectStorage:
    settings = get_settings()
    if settings.storage_backend == "s3":
        return S3ObjectStorage(settings)
    root = Path(settings.local_storage_path)
    return LocalObjectStorage(root, settings.minio_bucket)


async def init_storage() -> None:
    await get_storage().ensure_bucket()
