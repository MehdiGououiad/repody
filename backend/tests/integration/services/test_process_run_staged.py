"""Integration: real staged IDP→fraud handoff (Postgres + stub extractor + SKIPPED fraud)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from audit_workbench.db.models import (
    Document,
    Run,
    RunDispatchOutbox,
    RunDocument,
    RunStatus,
    SchemaField,
    Workflow,
    WorkflowStatus,
)
from audit_workbench.platform.contracts.agent import AgentId
from audit_workbench.services.run.processor import process_run
from audit_workbench.settings import clear_settings_cache


@pytest.fixture
async def staged_session(postgres_session, monkeypatch):
    monkeypatch.setenv("AUDIT_EXTRACTOR", "stub")
    monkeypatch.setenv("AUDIT_AGENT_IDP_ENABLED", "true")
    monkeypatch.setenv("AUDIT_AGENT_FRAUD_ENABLED", "true")
    monkeypatch.setenv("AUDIT_AGENT_FRAUD_WORKERS_READY", "true")
    monkeypatch.setenv("AUDIT_AGENT_COMPUTER_USE_ENABLED", "false")
    monkeypatch.setenv("AUDIT_AGENT_COMPUTER_USE_WORKERS_READY", "false")
    clear_settings_cache()
    # Avoid real Taskiq/Redis kiq during in-process staged processor tests.
    monkeypatch.setattr(
        "audit_workbench.services.run.handoff.schedule_outbox_dispatch",
        lambda _run_id: None,
    )

    wf = Workflow(id="wf-staged", name="Staged", status=WorkflowStatus.active.value)
    doc = Document(
        id="doc-staged",
        workflow_id=wf.id,
        document_type="Invoice",
        position=0,
        extraction_mode="document_model",
    )
    field = SchemaField(
        id="sf-staged",
        document_id=doc.id,
        name="total_amount",
        description="TTC",
        position=0,
    )
    run = Run(
        id="run-staged-1",
        workflow_id=wf.id,
        source="test",
        status=RunStatus.queued.value,
        worker_pool="extract",
    )
    run_doc = RunDocument(
        id="rdoc-staged",
        run_id=run.id,
        document_id=doc.id,
        document_type="Invoice",
    )
    postgres_session.add_all([wf, doc, field, run, run_doc])
    await postgres_session.flush()
    outbox = RunDispatchOutbox(
        run_id=run.id,
        pool="extract",
        agent_stage="idp",
        workflow_id=wf.id,
        status="dispatched",
        dispatch_attempts=1,
    )
    postgres_session.add(outbox)
    await postgres_session.commit()
    yield postgres_session
    clear_settings_cache()


@pytest.mark.asyncio
async def test_process_run_idp_stage_hands_off_to_fraud(staged_session):
    await process_run(staged_session, "run-staged-1", agent_stage="idp")

    run = await staged_session.get(Run, "run-staged-1")
    assert run is not None
    assert run.status == RunStatus.running.value
    assert run.worker_pool == "fraud"
    meta = run.run_metadata or {}
    outcomes = meta.get("agentOutcomes") or {}
    assert "idp" in outcomes
    assert "extraction" in outcomes["idp"]
    assert "validation" in outcomes["idp"]
    assert "pendingCompletion" in meta

    row = await staged_session.get(RunDispatchOutbox, "run-staged-1")
    assert row is not None
    assert row.agent_stage == AgentId.FRAUD.value
    assert row.pool == "fraud"
    assert row.status == "pending"


@pytest.mark.asyncio
async def test_process_run_fraud_stage_finalizes_pending(staged_session):
    # First stage must run for real so pendingCompletion + IDP payload are honest.
    await process_run(staged_session, "run-staged-1", agent_stage="idp")
    run = await staged_session.get(Run, "run-staged-1")
    assert run is not None
    assert run.worker_pool == "fraud"

    # Outbox may already be pending for fraud; claim path needs running + fraud stage.
    run.status = RunStatus.running.value
    run.started_at = run.started_at or datetime.now(UTC)
    await staged_session.commit()

    await process_run(staged_session, "run-staged-1", agent_stage="fraud")

    await staged_session.refresh(run)
    assert run.status == RunStatus.done.value
    assert run.overall_status == "passed"
    assert run.finished_at is not None
    meta = run.run_metadata or {}
    assert "pendingCompletion" not in meta
    outcomes = meta.get("agentOutcomes") or {}
    assert "fraud" in outcomes
    assert outcomes["fraud"].get("status") == "skipped"
