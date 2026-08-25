"""Integration: claim queued→running is idempotent against Postgres."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from repody.app.run.persistence import try_claim_queued_run
from repody.infra.db.models import Run, RunStatus, Workflow, WorkflowStatus


@pytest.fixture
async def claim_session(postgres_session):
    wf = Workflow(id="wf-claim", name="Claim", status=WorkflowStatus.active.value)
    run = Run(
        id="run-claim-1",
        workflow_id=wf.id,
        source="test",
        status=RunStatus.queued.value,
        worker_pool="extract",
    )
    postgres_session.add_all([wf, run])
    await postgres_session.commit()
    yield postgres_session


@pytest.mark.asyncio
async def test_try_claim_queued_run_once(claim_session):
    now = datetime.now(UTC)
    first = await try_claim_queued_run(claim_session, "run-claim-1", now)
    assert first is not None
    assert first.status.value == "running"
    assert first.started_at == now
    await claim_session.commit()

    second = await try_claim_queued_run(claim_session, "run-claim-1", datetime.now(UTC))
    assert second is None

    claim_session.expire_all()
    run = await claim_session.get(Run, "run-claim-1")
    assert run is not None
    assert run.status == RunStatus.running.value
    assert run.started_at is not None


@pytest.mark.asyncio
async def test_try_claim_missing_run_returns_none(claim_session):
    claimed = await try_claim_queued_run(claim_session, "run-missing", datetime.now(UTC))
    assert claimed is None
