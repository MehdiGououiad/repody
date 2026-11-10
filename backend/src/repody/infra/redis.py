"""One shared redis.asyncio client (connection pool) per process."""

from functools import lru_cache

import redis.asyncio as redis

from repody.settings import get_settings

# A hung connection fails fast instead of holding a request or a health probe.
SOCKET_TIMEOUT_SECONDS = 5


@lru_cache
def get_redis() -> redis.Redis:
    return redis.from_url(
        get_settings().redis_url.get_secret_value(),
        decode_responses=True,
        socket_timeout=SOCKET_TIMEOUT_SECONDS,
        socket_connect_timeout=SOCKET_TIMEOUT_SECONDS,
    )


async def close_redis() -> None:
    if get_redis.cache_info().currsize:
        await get_redis().aclose()
        get_redis.cache_clear()
