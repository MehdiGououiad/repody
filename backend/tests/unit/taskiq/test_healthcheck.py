"""Unit tests for Taskiq worker broker healthcheck."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from repody.taskiq.healthcheck import check_broker_ready


@pytest.mark.asyncio
async def test_check_broker_ready_ping_only_when_stream_missing():
    client = MagicMock()
    client.ping = AsyncMock(return_value=True)
    client.exists = AsyncMock(return_value=0)
    client.xinfo_stream = AsyncMock()
    client.aclose = AsyncMock()

    with patch("repody.taskiq.healthcheck.redis.from_url", return_value=client):
        await check_broker_ready(redis_url="redis://localhost:6379/0", pool="extract")

    client.ping.assert_awaited_once()
    client.exists.assert_awaited_once()
    client.xinfo_stream.assert_not_awaited()
    client.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_broker_ready_inspects_existing_stream():
    client = MagicMock()
    client.ping = AsyncMock(return_value=True)
    client.exists = AsyncMock(return_value=1)
    client.xinfo_stream = AsyncMock(return_value={"length": 0})
    client.aclose = AsyncMock()

    with patch("repody.taskiq.healthcheck.redis.from_url", return_value=client):
        await check_broker_ready(redis_url="redis://localhost:6379/0", pool="fast")

    client.xinfo_stream.assert_awaited_once_with("repody:audit:fast")


@pytest.mark.asyncio
async def test_check_broker_ready_fails_on_ping():
    client = MagicMock()
    client.ping = AsyncMock(side_effect=ConnectionError("down"))
    client.aclose = AsyncMock()

    with (
        patch("repody.taskiq.healthcheck.redis.from_url", return_value=client),
        pytest.raises(ConnectionError),
    ):
        await check_broker_ready(redis_url="redis://localhost:6379/0", pool="extract")

    client.aclose.assert_awaited_once()
