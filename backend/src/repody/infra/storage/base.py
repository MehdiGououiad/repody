"""Object storage contract (S3/MinIO in every deployment; tests swap in a fake)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PresignedPut:
    upload_url: str
    method: str = "PUT"
    headers: dict[str, str] = field(default_factory=dict)


class ObjectStore(Protocol):
    async def ensure_bucket(self) -> None: ...

    async def put_bytes(self, key: str, data: bytes, content_type: str) -> str: ...

    async def get_bytes(self, key: str) -> bytes: ...

    async def delete(self, key: str) -> None: ...

    async def stat_object(self, key: str) -> tuple[int, str | None]:
        """``(size, content_type)``; raises ``FileNotFoundError`` when missing."""
        ...

    async def head_bytes(self, key: str, *, max_bytes: int = 4096) -> bytes: ...

    async def presign_put(
        self, key: str, content_type: str, *, expires_seconds: int = 3600
    ) -> PresignedPut: ...
