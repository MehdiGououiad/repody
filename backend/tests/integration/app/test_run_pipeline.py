"""Run state machine, dispatch, and the worker pipeline (API -> worker -> stored results)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from tests.support.facture import (
    FACTURE_UI_PATHS,
    LOGIC_RULE_TOTAL_FAIL,
    LOGIC_RULE_TOTAL_OK,
    document_def,
    facture_bytes,
)

from repody.app.run import dispatch as dispatch_module
from repody.app.run.dispatch import dispatch_audit_run, redispatch_undispatched
from repody.app.run.state import claim_run, complete_run, fail_run
from repody.app.run.worker import execute_run_with_timeout, process_run
from repody.infra.db.models import RuleResult, Run, RunStatus, Workflow, WorkflowStatus


@pytest.fixture
async def session(postgres_session):
    postgres_session.add(Workflow(id="wf-state", name="State", status=WorkflowStatus.active.value))
    await postgres_session.commit()
    return postgres_session


def _run(run_id: str, status: RunStatus, **kwargs) -> Run:
    return Run(id=run_id, workflow_id="wf-state", status=status.value, **kwargs)


@pytest.mark.asyncio
async def test_claim_is_exactly_once(session):
    session.add(_run("r-claim", RunStatus.queued))
    await session.commit()
    now = datetime.now(UTC)
    assert await claim_run(session, "r-claim", now=now) == "wf-state"
    await session.commit()
    assert await claim_run(session, "r-claim", now=now) is None
    assert await claim_run(session, "r-missing", now=now) is None


@pytest.mark.asyncio
async def test_fail_respects_expected_status_and_terminal_states(session):
    session.add_all([_run("r-q", RunStatus.queued), _run("r-done", RunStatus.done)])
    await session.commit()
    assert not await fail_run("r-q", "nope", session=session, expected_status="running")
    assert not await fail_run("r-done", "nope", session=session)
    assert await fail_run("r-q", "x" * 5000, session=session)
    failed = await session.get(Run, "r-q", populate_existing=True)
    assert failed is not None
    assert failed.status == RunStatus.failed.value
    assert len(failed.error or "") == 4000
    assert (failed.progress or {}).get("failed") is True


@pytest.mark.asyncio
async def test_complete_only_from_running(session):
    session.add(_run("r-queued", RunStatus.queued))
    await session.commit()
    completed = await complete_run(
        session,
        "r-queued",
        overall_status="passed",
        summary_total=0,
        summary_passed=0,
        summary_failed=0,
        fields_extracted=0,
        run_metadata={},
        progress=None,
    )
    assert completed is False


@pytest.mark.asyncio
async def test_process_run_skips_a_run_that_is_not_queued(session):
    session.add(_run("r-running", RunStatus.running))
    await session.commit()
    await process_run("r-running")
    run = await session.get(Run, "r-running", populate_existing=True)
    assert run is not None and run.status == RunStatus.running.value


@pytest.mark.asyncio
async def test_redispatch_sends_only_old_undispatched_queued_runs(session, monkeypatch):
    old = datetime.now(UTC) - timedelta(minutes=5)
    session.add_all(
        [
            _run("r-lost", RunStatus.queued, created_at=old, worker_pool="extract"),
            _run("r-sent", RunStatus.queued, created_at=old, dispatched_at=old),
            _run("r-fresh", RunStatus.queued),
            _run("r-busy", RunStatus.running, created_at=old),
        ]
    )
    await session.commit()
    sent: list[tuple[str, str]] = []

    async def fake_dispatch(run_id, *, pool, workflow_id=None, request_id=None):
        sent.append((run_id, pool))
        return True

    monkeypatch.setattr(dispatch_module, "dispatch_audit_run", fake_dispatch)
    assert await redispatch_undispatched(session) == 1
    assert sent == [("r-lost", "extract")]


@pytest.mark.asyncio
async def test_failed_send_leaves_run_undispatched(session, monkeypatch):
    session.add(_run("r-down", RunStatus.queued))
    await session.commit()

    def broken_task(_pool):
        raise ConnectionError("redis down")

    monkeypatch.setattr(dispatch_module, "get_process_audit_run_task", broken_task)
    assert await dispatch_audit_run("r-down", pool="fast") is False
    run = await session.get(Run, "r-down", populate_existing=True)
    assert run is not None
    assert run.status == RunStatus.queued.value
    assert run.dispatched_at is None


@pytest.mark.asyncio
async def test_worker_extracts_and_validates_a_document(client, test_session_factory):
    """API creates the run; the worker extracts via (mocked) NuExtract and stores results."""
    suffix = uuid.uuid4().hex[:8]
    wf_id, doc_id = f"wf-pipe-{suffix}", f"doc-pipe-{suffix}"
    document = document_def(FACTURE_UI_PATHS[0], doc_id=doc_id)
    rules = [LOGIC_RULE_TOTAL_OK, LOGIC_RULE_TOTAL_FAIL]
    saved = await client.put(
        f"/v1/workflows/{wf_id}",
        json={"id": wf_id, "name": "Pipeline", "documents": [document], "rules": rules},
    )
    assert saved.status_code == 200, saved.text
    started = await client.post(
        f"/v1/workflows/{wf_id}/runs",
        files=[
            (
                "payload",
                (None, json.dumps({"documents": [document], "rules": rules}), "application/json"),
            ),
            ("document_ids", (None, json.dumps([doc_id]), "application/json")),
            ("files", ("Facture.pdf", facture_bytes(), "application/pdf")),
        ],
    )
    assert started.status_code == 202, started.text
    run_id = started.json()["runId"]

    await execute_run_with_timeout(run_id)

    detail = (await client.get(f"/v1/runs/{run_id}")).json()
    assert detail["status"] == "done", detail
    fields = {f["key"]: f["value"] for d in detail["result"]["documents"] for f in d["fields"]}
    assert fields["total_amount"] == "6000.00"
    statuses = {r["name"].split(":")[0]: r["status"] for r in detail["result"]["ruleResults"]}
    assert statuses == {"Total TTC equals 6000": "passed", "Total must not be 1": "failed"}
    assert detail["result"]["status"] == "failed"  # the failing rule has severity "reject"

    async with test_session_factory() as session:
        stored = (
            (await session.execute(select(RuleResult).where(RuleResult.run_id == run_id)))
            .scalars()
            .all()
        )
    assert len(stored) == 2
