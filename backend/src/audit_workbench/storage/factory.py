"""Select local vs S3 ObjectStore."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from audit_workbench.settings import get_settings
from audit_workbench.storage.base import ObjectStore
from audit_workbench.storage.local import build_local_store
from audit_workbench.storage.s3 import build_s3_store


@lru_cache
def get_storage() -> ObjectStore:
    settings = get_settings()
    if settings.storage_backend == "s3":
        return build_s3_store(settings)
    root = Path(settings.local_storage_path)
    return build_local_store(root, settings.minio_bucket)


async def init_storage() -> None:
    await get_storage().ensure_bucket()
