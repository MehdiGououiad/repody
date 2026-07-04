"""Taskiq Redis stream brokers — one queue per worker pool (ocr / fast)."""

from __future__ import annotations

import asyncio
from functools import lru_cache

import structlog
from taskiq_redis import RedisStreamBroker

from audit_workbench.settings import get_settings

log = structlog.get_logger(__name__)

QUEUE_PREFIX = "repody:audit:"
_broker_lock = asyncio.Lock()
_api_brokers_started = False


@lru_cache
def get_broker(pool: str) -> RedisStreamBroker:
    settings = get_settings()
    return RedisStreamBroker(
        url=settings.redis_url,
        queue_name=f"{QUEUE_PREFIX}{pool}",
    )


async def startup_taskiq_brokers() -> None:
    """Start broker connections on the API process (task producers)."""
    global _api_brokers_started
    async with _broker_lock:
        if _api_brokers_started:
            return
        settings = get_settings()
        for pool in (settings.worker_pool_ocr, settings.worker_pool_fast):
            broker = get_broker(pool)
            await broker.startup()
            log.info(
                "taskiq_broker_started",
                event_domain="taskiq",
                pool=pool,
                queue_name=f"{QUEUE_PREFIX}{pool}",
            )
        _api_brokers_started = True


async def shutdown_taskiq_brokers() -> None:
    global _api_brokers_started
    async with _broker_lock:
        if not _api_brokers_started:
            return
        settings = get_settings()
        for pool in (settings.worker_pool_ocr, settings.worker_pool_fast):
            broker = get_broker(pool)
            await broker.shutdown()
        _api_brokers_started = False
        get_broker.cache_clear()
        log.info("taskiq_brokers_shutdown", event_domain="taskiq")


def clear_broker_cache() -> None:
    """Reset cached brokers (tests)."""
    get_broker.cache_clear()
