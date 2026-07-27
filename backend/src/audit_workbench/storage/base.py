"""Object storage contracts — frozen DTOs + callable ops bundle (no ABC)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PresignedPut:
    upload_url: str
    method: str = "PUT"
    headers: dict[str, str] = field(default_factory=dict)


EnsureBucketFn = Callable[[], Awaitable[None]]
PutBytesFn = Callable[[str, bytes, str], Awaitable[str]]
GetBytesFn = Callable[[str], Awaitable[bytes]]
DeleteFn = Callable[[str], Awaitable[None]]
StatObjectFn = Callable[[str], Awaitable[tuple[int, str | None]]]
HeadBytesFn = Callable[..., Awaitable[bytes]]
GetRangeBytesFn = Callable[..., Awaitable[bytes]]
PresignPutFn = Callable[..., Awaitable[PresignedPut]]


@dataclass(frozen=True, slots=True)
class ObjectStore:
    """Injected storage operations — same attribute names as the old client API."""

    ensure_bucket: EnsureBucketFn
    put_bytes: PutBytesFn
    get_bytes: GetBytesFn
    delete: DeleteFn
    stat_object: StatObjectFn
    head_bytes: HeadBytesFn
    get_range_bytes: GetRangeBytesFn
    presign_put: PresignPutFn
