"""Shared Redis connection pool for cache, SSE pub/sub, and other API uses."""

from __future__ import annotations

import asyncio
from typing import Any

from audit_workbench.settings import get_settings

_redis: Any | None = None
_lock = asyncio.Lock()


async def get_redis():
    """Return a shared redis.asyncio client (connection pool)."""
    global _redis
    if _redis is not None:
        return _redis
    async with _lock:
        if _redis is None:
            import redis.asyncio as redis

            settings = get_settings()
            _redis = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                max_connections=settings.redis_max_connections,
            )
    return _redis


async def close_redis_pool() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
