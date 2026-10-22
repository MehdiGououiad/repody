"""Redis connectivity probe for readiness checks."""

from __future__ import annotations

from repody.infra.redis.pool import get_redis


async def ping_redis() -> bool:
    """Return True when Redis responds to PING."""
    try:
        client = await get_redis()
        return bool(await client.ping())
    except Exception:
        return False
