"""Readiness probe against real Postgres + Redis — no mocked connectivity."""

from __future__ import annotations

import pytest

from audit_workbench.app.health import is_readiness_ok, probe_readiness
from audit_workbench.infra.redis.health import ping_redis
from audit_workbench.infra.redis.pool import close_redis_pool
from audit_workbench.settings import clear_settings_cache


@pytest.mark.asyncio
async def test_readiness_ok_when_redis_and_postgres_up(postgres_session):
    _ = postgres_session
    if not await ping_redis():
        pytest.skip("Redis must be reachable at AUDIT_REDIS_URL for readiness integration")
    body = await probe_readiness()
    assert body.redis_ok is True
    assert body.status == "ok"
    assert is_readiness_ok(body) is True


@pytest.mark.asyncio
async def test_readiness_degraded_when_redis_unreachable(postgres_session, monkeypatch):
    _ = postgres_session
    monkeypatch.setenv("AUDIT_REDIS_URL", "redis://127.0.0.1:1/15")
    clear_settings_cache()
    await close_redis_pool()
    try:
        body = await probe_readiness()
    finally:
        monkeypatch.delenv("AUDIT_REDIS_URL", raising=False)
        clear_settings_cache()
        await close_redis_pool()
    assert body.redis_ok is False
    assert body.status == "degraded"
    assert is_readiness_ok(body) is False
