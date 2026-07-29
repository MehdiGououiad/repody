"""Unit tests for stage-aware stale reap (no Postgres)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from audit_workbench.app.maintenance import _running_activity_at, maybe_reap_stale_run


def test_running_activity_prefers_last_activity_at():
    run = SimpleNamespace(
        last_activity_at=datetime(2026, 7, 1, tzinfo=UTC),
        started_at=datetime(2020, 1, 1, tzinfo=UTC),
    )
    assert _running_activity_at(run) == run.last_activity_at


def test_running_activity_falls_back_to_started_at():
    run = SimpleNamespace(last_activity_at=None, started_at=datetime(2020, 1, 1, tzinfo=UTC))
    assert _running_activity_at(run) == run.started_at


@pytest.mark.asyncio
async def test_maybe_reap_stale_run_uses_activity_clock(monkeypatch: pytest.MonkeyPatch):
    fail = AsyncMock(return_value=True)
    monkeypatch.setattr("audit_workbench.app.maintenance.fail_run_terminal", fail)
    monkeypatch.setattr(
        "audit_workbench.app.maintenance.get_settings",
        lambda: SimpleNamespace(stale_run_timeout_minutes=20, queued_stale_timeout_minutes=5),
    )
    # Old start, fresh activity → do not reap
    run = SimpleNamespace(
        id="run-1",
        status="running",
        started_at=datetime(2020, 1, 1, tzinfo=UTC),
        last_activity_at=datetime.now(UTC) - timedelta(minutes=2),
        created_at=datetime.now(UTC),
    )
    session = AsyncMock()
    assert await maybe_reap_stale_run(session, run) is False
    fail.assert_not_awaited()

    # Stale activity → reap
    run.last_activity_at = datetime(2020, 1, 1, tzinfo=UTC)
    assert await maybe_reap_stale_run(session, run) is True
    fail.assert_awaited_once()
