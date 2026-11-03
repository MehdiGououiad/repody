"""The process-wide object store."""

from __future__ import annotations

from repody.infra.storage.base import ObjectStore
from repody.infra.storage.s3 import S3Store
from repody.settings import get_settings

_store: ObjectStore | None = None


def get_storage() -> ObjectStore:
    global _store
    if _store is None:
        _store = S3Store(get_settings())
    return _store


def use_storage(store: ObjectStore | None) -> None:
    """Replace the process-wide store (tests install an in-memory one; None resets)."""
    global _store
    _store = store


async def init_storage() -> None:
    await get_storage().ensure_bucket()
