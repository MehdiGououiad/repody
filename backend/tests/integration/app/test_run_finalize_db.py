"""Integration: finalize_pending_completion completes a real Postgres run."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from repody.infra.db.models import Run, RunStatus, Workflow, WorkflowStatus
from repody.runtime.agent_metadata import PendingCompletion, store_pending_completion
from repody.app.run.commands import finalize_pending_completion


@pytest.fixture
async def finalize_session(postgres_session):
    wf = Workflow(id="wf-finalize", name="Finalize", status=WorkflowStatus.active.value)
    run = Run(
        id="run-finalize-1",
        workflow_id=wf.id,
        source="test",
        status=RunStatus.running.value,
        worker_pool="fraud",
        started_at=datetime.now(UTC),
    )
    store_pending_completion(
        run,
        PendingCompletion(
            overall_status="passed",
            summary_total=1,
            summary_passed=1,
            summary_failed=0,
            fields_extracted=2,
            run_metadata={"durationMs": 12},
            progress=None,
        ),
    )
    # Outcomes recorded after pending was stored (IDP + later agents).
    meta = dict(run.run_metadata or {})
    meta["agentOutcomes"] = {
        "idp": {"status": "passed", "overallStatus": "passed"},
        "fraud": {"status": "skipped", "summary": "skipped: not implemented"},
    }
    run.run_metadata = meta
    postgres_session.add_all([wf, run])
    await postgres_session.commit()
    yield postgres_session


@pytest.mark.asyncio
async def test_finalize_pending_completion_marks_run_done(finalize_session):
    run = await finalize_session.get(Run, "run-finalize-1")
    assert run is not None
    await finalize_pending_completion(finalize_session, run)

    await finalize_session.refresh(run)
    assert run.status == RunStatus.done.value
    assert run.overall_status == "passed"
    assert run.summary_passed == 1
    assert run.fields_extracted == 2
    assert run.finished_at is not None
    meta = run.run_metadata or {}
    assert "pendingCompletion" not in meta
    assert meta.get("durationMs") == 12
    outcomes = meta.get("agentOutcomes") or {}
    assert "idp" in outcomes
    assert "fraud" in outcomes


@pytest.mark.asyncio
async def test_finalize_pending_completion_requires_payload(finalize_session):
    run = await finalize_session.get(Run, "run-finalize-1")
    assert run is not None
    run.run_metadata = {}
    await finalize_session.commit()

    with pytest.raises(RuntimeError, match="missing pendingCompletion"):
        await finalize_pending_completion(finalize_session, run)
