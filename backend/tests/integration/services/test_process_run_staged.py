"""Integration: process_run staged IDP→fraud handoff and fraud finalize (DB + mocks)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from audit_workbench.agents.fraud.contracts import FraudOutcome
from audit_workbench.agents.idp.contracts import ExtractionOutput, IdpOutcome, ValidationOutput
from audit_workbench.db.models import (
    Run,
    RunDispatchOutbox,
    RunStatus,
    Workflow,
    WorkflowStatus,
)
from audit_workbench.platform.agent_metadata import (
    PendingCompletion,
    record_agent_outcome,
    store_pending_completion,
)
from audit_workbench.platform.contracts.agent import AgentId, AgentOutcome, AgentStatus
from audit_workbench.platform.contracts.result import Result
from audit_workbench.platform.recipe import PlatformStageResult
from audit_workbench.services.run.processor import process_run


def _flags(**overrides):
    base = dict(
        agent_idp_enabled=True,
        agent_fraud_enabled=True,
        agent_fraud_workers_ready=True,
        agent_computer_use_enabled=False,
        agent_computer_use_workers_ready=False,
        worker_task_timeout_minutes=30,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _idp_outcome(run_id: str) -> IdpOutcome:
    return IdpOutcome(
        run_id=run_id,
        workflow_id="wf-staged",
        extraction=ExtractionOutput(by_document=()),
        validation=ValidationOutput(
            rule_results=(),
            overall_status="passed",
            summary_passed=0,
            summary_failed=0,
        ),
    )


@pytest.fixture
async def staged_session(postgres_session):
    wf = Workflow(id="wf-staged", name="Staged", status=WorkflowStatus.active.value)
    run = Run(
        id="run-staged-1",
        workflow_id=wf.id,
        source="test",
        status=RunStatus.queued.value,
        worker_pool="extract",
    )
    postgres_session.add_all([wf, run])
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


@pytest.mark.asyncio
async def test_process_run_idp_stage_hands_off_to_fraud(staged_session, monkeypatch):
    monkeypatch.setattr(
        "audit_workbench.services.run.processor.get_settings",
        lambda: _flags(),
    )
    monkeypatch.setattr(
        "audit_workbench.platform.recipe.get_settings",
        lambda: _flags(),
    )
    monkeypatch.setattr(
        "audit_workbench.services.run.handoff.schedule_outbox_dispatch",
        lambda _run_id: None,
    )

    async def _fake_platform_run(session, run, *, agent_stage=None, **_kwargs):
        assert agent_stage is AgentId.IDP
        store_pending_completion(
            run,
            PendingCompletion(
                overall_status="passed",
                summary_total=0,
                summary_passed=0,
                summary_failed=0,
                fields_extracted=0,
                run_metadata={},
            ),
        )
        outcome = AgentOutcome(
            agent=AgentId.IDP,
            status=AgentStatus.PASSED,
            payload=_idp_outcome(run.id),
        )
        record_agent_outcome(run, outcome)
        await session.commit()
        return PlatformStageResult(
            outcome=outcome,
            next_agent=AgentId.FRAUD,
            recipe=(AgentId.IDP, AgentId.FRAUD),
            finalize_pending=False,
        )

    monkeypatch.setattr(
        "audit_workbench.services.run.processor.execute_platform_run",
        _fake_platform_run,
    )

    await process_run(staged_session, "run-staged-1", agent_stage="idp")

    run = await staged_session.get(Run, "run-staged-1")
    assert run is not None
    assert run.status == RunStatus.running.value
    assert run.worker_pool == "fraud"
    row = await staged_session.get(RunDispatchOutbox, "run-staged-1")
    assert row is not None
    assert row.agent_stage == "fraud"
    assert row.pool == "fraud"
    assert row.status == "pending"


@pytest.mark.asyncio
async def test_process_run_fraud_stage_finalizes_pending(staged_session, monkeypatch):
    monkeypatch.setattr(
        "audit_workbench.services.run.processor.get_settings",
        lambda: _flags(),
    )
    monkeypatch.setattr(
        "audit_workbench.platform.recipe.get_settings",
        lambda: _flags(),
    )
    publish = AsyncMock()
    monkeypatch.setattr(
        "audit_workbench.services.run.finalize.publish_run_domain_events",
        publish,
    )

    run = await staged_session.get(Run, "run-staged-1")
    assert run is not None
    run.status = RunStatus.running.value
    run.worker_pool = "fraud"
    run.started_at = datetime.now(UTC)
    store_pending_completion(
        run,
        PendingCompletion(
            overall_status="passed",
            summary_total=1,
            summary_passed=1,
            summary_failed=0,
            fields_extracted=1,
            run_metadata={},
        ),
    )
    record_agent_outcome(
        run,
        AgentOutcome(
            agent=AgentId.IDP,
            status=AgentStatus.PASSED,
            payload=_idp_outcome(run.id),
        ),
    )
    await staged_session.commit()

    async def _fake_platform_run(session, run, *, agent_stage=None, **_kwargs):
        assert agent_stage is AgentId.FRAUD
        outcome = AgentOutcome(
            agent=AgentId.FRAUD,
            status=AgentStatus.SKIPPED,
            payload=FraudOutcome(run_id=run.id, summary="skipped"),
        )
        record_agent_outcome(run, outcome)
        await session.commit()
        return PlatformStageResult(
            outcome=outcome,
            next_agent=None,
            recipe=(AgentId.IDP, AgentId.FRAUD),
            finalize_pending=True,
        )

    monkeypatch.setattr(
        "audit_workbench.services.run.processor.execute_platform_run",
        _fake_platform_run,
    )

    await process_run(staged_session, "run-staged-1", agent_stage="fraud")

    await staged_session.refresh(run)
    assert run.status == RunStatus.done.value
    assert run.overall_status == "passed"
    assert run.finished_at is not None
    meta = run.run_metadata or {}
    assert "pendingCompletion" not in meta
    publish.assert_awaited()
