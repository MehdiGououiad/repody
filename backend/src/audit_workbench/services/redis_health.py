"""Redis connectivity probe for readiness checks."""

from __future__ import annotations


async def ping_redis() -> bool:
    """Return True when Redis responds to PING."""
    try:
        from audit_workbench.services.redis_pool import get_redis

        client = await get_redis()
        pong = await client.ping()
        return bool(pong)
    except Exception:
        return False
