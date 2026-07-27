"""Local filesystem object store as plain functions + ObjectStore binder."""

from __future__ import annotations

import asyncio
from pathlib import Path

from audit_workbench.storage.base import ObjectStore, PresignedPut


def _safe_path(root: Path, key: str) -> Path:
    safe = key.replace("\\", "/").lstrip("/")
    path = (root / safe).resolve()
    resolved_root = root.resolve()
    if resolved_root not in path.parents and path != resolved_root:
        raise ValueError("Invalid storage key path.")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def build_local_store(root: Path, bucket: str) -> ObjectStore:
    bucket_root = root / bucket
    bucket_root.mkdir(parents=True, exist_ok=True)

    async def ensure_bucket() -> None:
        bucket_root.mkdir(parents=True, exist_ok=True)

    async def put_bytes(key: str, data: bytes, content_type: str) -> str:
        _ = content_type
        path = _safe_path(bucket_root, key)
        await asyncio.to_thread(path.write_bytes, data)
        return key

    async def get_bytes(key: str) -> bytes:
        path = _safe_path(bucket_root, key)
        return await asyncio.to_thread(path.read_bytes)

    async def stat_object(key: str) -> tuple[int, str | None]:
        path = _safe_path(bucket_root, key)
        if not path.exists():
            raise FileNotFoundError(key)
        return path.stat().st_size, None

    async def head_bytes(key: str, *, max_bytes: int = 4096) -> bytes:
        path = _safe_path(bucket_root, key)

        def _read_prefix() -> bytes:
            with path.open("rb") as fh:
                return fh.read(max_bytes)

        return await asyncio.to_thread(_read_prefix)

    async def get_range_bytes(key: str, *, start: int, end: int) -> bytes:
        _ = (key, start, end)
        raise NotImplementedError("Local storage does not support ranged reads")

    async def delete(key: str) -> None:
        path = _safe_path(bucket_root, key)
        if path.exists():
            await asyncio.to_thread(path.unlink)

    async def presign_put(
        key: str,
        content_type: str,
        *,
        expires_seconds: int = 3600,
    ) -> PresignedPut:
        _ = (key, content_type, expires_seconds)
        raise NotImplementedError("Local storage does not support presigned uploads")

    return ObjectStore(
        ensure_bucket=ensure_bucket,
        put_bytes=put_bytes,
        get_bytes=get_bytes,
        delete=delete,
        stat_object=stat_object,
        head_bytes=head_bytes,
        get_range_bytes=get_range_bytes,
        presign_put=presign_put,
    )
