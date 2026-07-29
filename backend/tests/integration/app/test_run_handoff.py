"""Integration: agent-stage handoff persists outbox + pool against Postgres."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from audit_workbench.infra.db.models import (
    Run,
    RunDispatchOutbox,
    RunStatus,
    Workflow,
    WorkflowStatus,
)
from audit_workbench.runtime.contracts.agent import AgentId
from audit_workbench.app.run.handoff import schedule_next_agent_stage


@pytest.fixture
async def handoff_session(postgres_session, monkeypatch):
    monkeypatch.setattr(
        "audit_workbench.app.run.handoff.schedule_outbox_dispatch",
        lambda _run_id: None,
    )
    wf = Workflow(id="wf-handoff", name="Handoff", status=WorkflowStatus.active.value)
    run = Run(
        id="run-handoff-1",
        workflow_id=wf.id,
        source="test",
        status=RunStatus.running.value,
        worker_pool="extract",
        last_activity_at=datetime(2020, 1, 1, tzinfo=UTC),
    )
    postgres_session.add_all([wf, run])
    await postgres_session.flush()
    outbox = RunDispatchOutbox(
        run_id=run.id,
        pool="extract",
        agent_stage="idp",
        workflow_id=wf.id,
        status="dispatched",
        dispatch_attempts=2,
    )
    postgres_session.add(outbox)
    await postgres_session.commit()
    yield postgres_session


@pytest.mark.asyncio
async def test_schedule_next_agent_stage_reuses_outbox(handoff_session):
    run = await handoff_session.get(Run, "run-handoff-1")
    assert run is not None
    await schedule_next_agent_stage(
        handoff_session,
        run,
        AgentId.FRAUD,
        request_id="req-handoff",
    )

    await handoff_session.refresh(run)
    assert run.worker_pool == "fraud"
    assert run.last_activity_at is not None
    assert run.last_activity_at > datetime(2020, 1, 1, tzinfo=UTC)

    row = await handoff_session.get(RunDispatchOutbox, "run-handoff-1")
    assert row is not None
    assert row.pool == "fraud"
    assert row.agent_stage == "fraud"
    assert row.status == "pending"
    assert row.dispatch_attempts == 0
    assert row.request_id == "req-handoff"


@pytest.mark.asyncio
async def test_schedule_next_agent_stage_creates_outbox_when_missing(handoff_session):
    row = await handoff_session.get(RunDispatchOutbox, "run-handoff-1")
    assert row is not None
    await handoff_session.delete(row)
    await handoff_session.commit()

    run = await handoff_session.get(Run, "run-handoff-1")
    assert run is not None
    await schedule_next_agent_stage(handoff_session, run, AgentId.COMPUTER_USE)

    created = await handoff_session.get(RunDispatchOutbox, "run-handoff-1")
    assert created is not None
    assert created.pool == "computer_use"
    assert created.agent_stage == "computer_use"
    assert created.status == "pending"
