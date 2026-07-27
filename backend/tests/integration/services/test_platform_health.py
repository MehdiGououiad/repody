from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

from audit_workbench.services.platform_health import is_readiness_ok, probe_readiness


@asynccontextmanager
async def _fake_session():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=None)
    yield session


@pytest.mark.asyncio
async def test_readiness_ok_when_redis_pings():
    with (
        patch(
            "audit_workbench.services.platform_health.ping_redis",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "audit_workbench.services.platform_health.db_base.async_session_factory",
            _fake_session,
        ),
        patch(
            "audit_workbench.services.platform_health.count_queued",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "audit_workbench.services.platform_health.count_running",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "audit_workbench.services.platform_health.count_inflight",
            new=AsyncMock(return_value=0),
        ),
    ):
        body = await probe_readiness()
    assert body.redis_ok is True
    assert body.status == "ok"
    assert is_readiness_ok(body) is True


@pytest.mark.asyncio
async def test_readiness_degraded_when_redis_down():
    with (
        patch(
            "audit_workbench.services.platform_health.ping_redis",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "audit_workbench.services.platform_health.db_base.async_session_factory",
            _fake_session,
        ),
        patch(
            "audit_workbench.services.platform_health.count_queued",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "audit_workbench.services.platform_health.count_running",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "audit_workbench.services.platform_health.count_inflight",
            new=AsyncMock(return_value=0),
        ),
    ):
        body = await probe_readiness()
    assert body.redis_ok is False
    assert body.status == "degraded"
    assert is_readiness_ok(body) is False
