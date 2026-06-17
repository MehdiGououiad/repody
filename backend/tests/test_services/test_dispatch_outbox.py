from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from audit_workbench.db.models import Run, RunDispatchOutbox, RunStatus, Workflow, WorkflowStatus
from audit_workbench.services.dispatch_outbox import (
    dispatch_outbox_row,
    enqueue_dispatch,
    replay_dispatch_outbox,
)


@pytest.fixture
async def outbox_session(postgres_session):
    wf = Workflow(id="wf-outbox", name="Outbox", status=WorkflowStatus.active.value)
    postgres_session.add(wf)
    run = Run(id="run-outbox", workflow_id="wf-outbox", status=RunStatus.queued.value)
    postgres_session.add(run)
    await postgres_session.commit()
    yield postgres_session


@pytest.mark.asyncio
async def test_dispatch_outbox_retries_transient_errors(outbox_session, monkeypatch):
    session = outbox_session
    await enqueue_dispatch(
        session,
        run_id="run-outbox",
        pool="fast",
        workflow_id="wf-outbox",
        request_id="req-1",
    )
    await session.commit()

    row = await session.get(RunDispatchOutbox, "run-outbox")
    assert row is not None
    assert row.status == "pending"

    dispatch = AsyncMock(side_effect=[ConnectionError("connection refused"), None])
    monkeypatch.setattr(
        "audit_workbench.services.run_dispatch.dispatch_audit_run",
        dispatch,
    )
    monkeypatch.setattr(
        "audit_workbench.services.dispatch_outbox.get_settings",
        lambda: type("S", (), {"dispatch_max_attempts": 8})(),
    )

    assert await dispatch_outbox_row(session, row) is False
    assert row.status == "pending"
    assert row.dispatch_attempts == 1

    assert await dispatch_outbox_row(session, row) is True
    assert row.status == "dispatched"
    assert row.dispatch_attempts == 2
    assert dispatch.await_count == 2


@pytest.mark.asyncio
async def test_replay_dispatch_outbox_picks_pending_rows(outbox_session, monkeypatch):
    session = outbox_session
    await enqueue_dispatch(
        session,
        run_id="run-outbox",
        pool="fast",
        workflow_id="wf-outbox",
        request_id=None,
    )
    await session.commit()

    dispatch = AsyncMock()
    monkeypatch.setattr(
        "audit_workbench.services.run_dispatch.dispatch_audit_run",
        dispatch,
    )
    monkeypatch.setattr(
        "audit_workbench.services.dispatch_outbox.get_settings",
        lambda: type("S", (), {"dispatch_max_attempts": 8})(),
    )

    dispatched = await replay_dispatch_outbox(session, limit=10)
    assert dispatched == 1
    assert dispatch.await_count == 1

    row = await session.get(RunDispatchOutbox, "run-outbox")
    assert row is not None
    assert row.status == "dispatched"
