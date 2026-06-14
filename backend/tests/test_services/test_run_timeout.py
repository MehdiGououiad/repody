from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from audit_workbench.services.run_processor import execute_run_with_timeout


@pytest.mark.asyncio
async def test_execute_run_with_timeout_fails_run(monkeypatch):
    session = AsyncMock()
    session.rollback = AsyncMock()

    async def slow_run(_session, _run_id):
        import asyncio

        await asyncio.sleep(10)

    monkeypatch.setattr(
        "audit_workbench.services.run_processor.process_run",
        slow_run,
    )
    monkeypatch.setattr(
        "audit_workbench.services.run_processor.get_settings",
        lambda: type(
            "S",
            (),
            {"hatchet_task_timeout_minutes": 0},
        )(),
    )
    fail = AsyncMock(return_value=True)
    monkeypatch.setattr("audit_workbench.services.run_processor.fail_run_terminal", fail)

    with pytest.raises(TimeoutError):
        await execute_run_with_timeout(session, "run-timeout-test")

    session.rollback.assert_awaited_once()
    fail.assert_awaited_once()
    assert "task timeout" in fail.await_args.args[1].lower()
