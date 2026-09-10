"""Worker readiness check — Redis/broker reachability for K8s readiness probes.

Taskiq has no first-class health CLI yet (see taskiq#240). Kubernetes readiness
should prove the worker can reach its broker. Keep liveness process-local so a
Redis outage does not restart every worker (Kubernetes probe guidance).

Use::

    python -m repody.taskiq.healthcheck
"""

from __future__ import annotations

import asyncio
import sys

import redis.asyncio as redis

from repody.settings import get_settings
from repody.taskiq.broker import QUEUE_PREFIX


async def check_broker_ready(*, redis_url: str, pool: str, timeout: float = 3.0) -> None:
    """PING Redis and touch the pool stream key when it already exists."""
    client = redis.from_url(redis_url, socket_connect_timeout=timeout, socket_timeout=timeout)
    try:
        pong = await client.ping()
        if not pong:
            raise RuntimeError("redis PING returned falsy")
        queue_name = f"{QUEUE_PREFIX}{pool}"
        exists = await client.exists(queue_name)
        if exists:
            # Confirms the key is a stream we can inspect (broker-shaped).
            await client.xinfo_stream(queue_name)
    finally:
        await client.aclose()


def main() -> None:
    settings = get_settings()
    pool = settings.worker_pool
    try:
        asyncio.run(check_broker_ready(redis_url=settings.redis_url, pool=pool))
    except Exception as exc:
        sys.stderr.write(f"worker broker not ready: {exc}\n")
        raise SystemExit(1) from exc
    sys.stdout.write(f"ok pool={pool}\n")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
