from __future__ import annotations

import asyncio
from pathlib import Path

from audit_workbench.storage.base import ObjectStorage


class LocalObjectStorage(ObjectStorage):
    def __init__(self, root: Path, bucket: str) -> None:
        self._root = root / bucket
        self._root.mkdir(parents=True, exist_ok=True)

    async def ensure_bucket(self) -> None:
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = key.replace("\\", "/").lstrip("/")
        path = (self._root / safe).resolve()
        root = self._root.resolve()
        if root not in path.parents and path != root:
            raise ValueError("Invalid storage key path.")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    async def put_bytes(self, key: str, data: bytes, content_type: str) -> str:
        _ = content_type
        path = self._path(key)
        await asyncio.to_thread(path.write_bytes, data)
        return key

    async def get_bytes(self, key: str) -> bytes:
        path = self._path(key)
        return await asyncio.to_thread(path.read_bytes)

    async def stat_object(self, key: str) -> tuple[int, str | None]:
        path = self._path(key)
        if not path.exists():
            raise FileNotFoundError(key)
        return path.stat().st_size, None

    async def head_bytes(self, key: str, *, max_bytes: int = 4096) -> bytes:
        path = self._path(key)

        def _read_prefix() -> bytes:
            with path.open("rb") as fh:
                return fh.read(max_bytes)

        return await asyncio.to_thread(_read_prefix)

    async def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            await asyncio.to_thread(path.unlink)
