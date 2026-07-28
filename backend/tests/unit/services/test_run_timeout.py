from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from audit_workbench.services.run.processor import execute_run_with_timeout


@pytest.mark.asyncio
async def test_execute_run_with_timeout_fails_run(monkeypatch):
    session = AsyncMock()
    session.rollback = AsyncMock()

    async def slow_run(_session, _run_id, **_kwargs):
        import asyncio

        await asyncio.sleep(10)

    monkeypatch.setattr(
        "audit_workbench.services.run.processor.process_run",
        slow_run,
    )
    monkeypatch.setattr(
        "audit_workbench.services.run.processor.get_settings",
        lambda: type(
            "S",
            (),
            {"worker_task_timeout_minutes": 0},
        )(),
    )
    fail = AsyncMock(return_value=True)
    monkeypatch.setattr("audit_workbench.services.run.processor.fail_run_terminal", fail)

    with pytest.raises(TimeoutError):
        await execute_run_with_timeout("run-timeout-test", session=session)

    session.rollback.assert_awaited_once()
    fail.assert_awaited_once()
    assert "task timeout" in fail.await_args.args[1].lower()
