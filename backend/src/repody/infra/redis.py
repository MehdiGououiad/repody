"""One shared redis.asyncio client (connection pool) per process."""

from __future__ import annotations

from functools import lru_cache

import redis.asyncio as redis

from repody.settings import get_settings


@lru_cache
def get_redis() -> redis.Redis:
    return redis.from_url(get_settings().redis_url, decode_responses=True)


async def close_redis() -> None:
    if get_redis.cache_info().currsize:
        await get_redis().aclose()
        get_redis.cache_clear()
