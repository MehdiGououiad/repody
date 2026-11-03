"""In-memory ObjectStore for in-process tests (production always uses S3/MinIO)."""

from __future__ import annotations

from repody.infra.storage.base import PresignedPut


class MemoryStore:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    async def ensure_bucket(self) -> None:
        return None

    async def put_bytes(self, key: str, data: bytes, content_type: str) -> str:
        self.objects[key] = (data, content_type)
        return key

    async def get_bytes(self, key: str) -> bytes:
        try:
            return self.objects[key][0]
        except KeyError:
            raise FileNotFoundError(key) from None

    async def delete(self, key: str) -> None:
        self.objects.pop(key, None)

    async def stat_object(self, key: str) -> tuple[int, str | None]:
        data = await self.get_bytes(key)
        return len(data), self.objects[key][1]

    async def head_bytes(self, key: str, *, max_bytes: int = 4096) -> bytes:
        return (await self.get_bytes(key))[:max_bytes]

    async def presign_put(
        self, key: str, content_type: str, *, expires_seconds: int = 3600
    ) -> PresignedPut:
        _ = expires_seconds
        return PresignedPut(
            upload_url=f"http://storage.test/{key}", headers={"Content-Type": content_type}
        )
