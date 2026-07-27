"""P0 scalability: handoff pool/activity (real Postgres) and skip-locked dialect gate."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from audit_workbench.db.models import Run, RunDispatchOutbox, RunStatus, Workflow, WorkflowStatus
from audit_workbench.platform.contracts.agent import AgentId
from audit_workbench.services.dispatch_outbox import _supports_skip_locked
from audit_workbench.services.run.handoff import schedule_next_agent_stage


@pytest.fixture
async def handoff_session(postgres_session):
    wf = Workflow(id="wf-p0", name="P0", status=WorkflowStatus.active.value)
    run = Run(
        id="run-p0-1",
        workflow_id=wf.id,
        source="test",
        status=RunStatus.running.value,
        worker_pool="extract",
        started_at=datetime(2020, 1, 1, tzinfo=UTC),
        last_activity_at=datetime(2020, 1, 1, tzinfo=UTC),
    )
    postgres_session.add_all([wf, run])
    await postgres_session.commit()
    yield postgres_session


def test_supports_skip_locked_only_on_postgres():
    pg = SimpleNamespace(get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")))
    assert _supports_skip_locked(pg) is True

    sqlite = SimpleNamespace(get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="sqlite")))
    assert _supports_skip_locked(sqlite) is False


@pytest.mark.asyncio
async def test_handoff_updates_worker_pool_and_activity(handoff_session):
    run = await handoff_session.get(Run, "run-p0-1")
    assert run is not None
    before = run.last_activity_at

    await schedule_next_agent_stage(handoff_session, run, AgentId.FRAUD, request_id="req-1")

    await handoff_session.refresh(run)
    assert run.worker_pool == "fraud"
    assert run.last_activity_at is not None
    assert before is None or run.last_activity_at > before

    row = await handoff_session.get(RunDispatchOutbox, "run-p0-1")
    assert row is not None
    assert row.pool == "fraud"
    assert row.agent_stage == "fraud"
    assert row.status == "pending"
