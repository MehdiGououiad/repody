from __future__ import annotations

from abc import ABC, abstractmethod


class PresignedPut:
    def __init__(
        self,
        *,
        upload_url: str,
        method: str = "PUT",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.upload_url = upload_url
        self.method = method
        self.headers = headers or {}


class ObjectStorage(ABC):
    @abstractmethod
    async def ensure_bucket(self) -> None: ...

    @abstractmethod
    async def put_bytes(self, key: str, data: bytes, content_type: str) -> str: ...

    @abstractmethod
    async def get_bytes(self, key: str) -> bytes: ...

    async def stat_object(self, key: str) -> tuple[int, str | None]:
        """Return (size_bytes, content_type). Raises FileNotFoundError when missing."""
        data = await self.get_bytes(key)
        return len(data), None

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    async def presign_put(
        self,
        key: str,
        content_type: str,
        *,
        expires_seconds: int = 3600,
    ) -> PresignedPut:
        raise NotImplementedError(f"{type(self).__name__} does not support presigned uploads")

    async def head_bytes(self, key: str, *, max_bytes: int = 4096) -> bytes:
        return await self.get_range_bytes(key, start=0, end=max_bytes)

    async def get_range_bytes(self, key: str, *, start: int, end: int) -> bytes:
        _ = (key, start, end)
        raise NotImplementedError(f"{type(self).__name__} does not support ranged reads")
