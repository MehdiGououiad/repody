from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from audit_workbench.services.platform_health import is_readiness_ok, probe_readiness


@pytest.mark.asyncio
async def test_readiness_ok_when_redis_pings():
    with patch(
        "audit_workbench.services.platform_health.ping_redis",
        new=AsyncMock(return_value=True),
    ):
        body = await probe_readiness()
    assert body.redis_ok is True
    assert body.status == "ok"
    assert is_readiness_ok(body) is True


@pytest.mark.asyncio
async def test_readiness_degraded_when_redis_down():
    with patch(
        "audit_workbench.services.platform_health.ping_redis",
        new=AsyncMock(return_value=False),
    ):
        body = await probe_readiness()
    assert body.redis_ok is False
    assert body.status == "degraded"
    assert is_readiness_ok(body) is False
