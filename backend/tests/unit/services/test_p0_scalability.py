"""P0 scalability hardening: handoff pool, activity clock, stage idempotency, outbox lock."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from audit_workbench.agents.fraud.contracts import FraudOutcome
from audit_workbench.platform.agent_metadata import record_agent_outcome
from audit_workbench.platform.contracts.agent import AgentId, AgentOutcome, AgentStatus
from audit_workbench.services.dispatch_outbox import _supports_skip_locked
from audit_workbench.services.run.handoff import schedule_next_agent_stage
from audit_workbench.services.run.processor import _resume_after_recorded_stage


@pytest.mark.asyncio
async def test_handoff_updates_worker_pool_and_activity(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "audit_workbench.services.run.handoff.schedule_outbox_dispatch",
        lambda _run_id: None,
    )
    run = SimpleNamespace(
        id="run-1",
        workflow_id="wf-1",
        worker_pool="extract",
        last_activity_at=datetime(2020, 1, 1, tzinfo=UTC),
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.commit = AsyncMock()
    session.add = MagicMock()

    await schedule_next_agent_stage(session, run, AgentId.FRAUD, request_id="req-1")

    assert run.worker_pool == "fraud"
    assert run.last_activity_at is not None
    assert run.last_activity_at > datetime(2020, 1, 1, tzinfo=UTC)
    session.add.assert_called_once()
    added = session.add.call_args.args[0]
    assert added.pool == "fraud"
    assert added.agent_stage == "fraud"
    session.commit.assert_awaited_once()


def test_supports_skip_locked_only_on_postgres():
    pg = MagicMock()
    pg.get_bind.return_value.dialect.name = "postgresql"
    assert _supports_skip_locked(pg) is True

    sqlite = MagicMock()
    sqlite.get_bind.return_value.dialect.name = "sqlite"
    assert _supports_skip_locked(sqlite) is False


@pytest.mark.asyncio
async def test_resume_after_recorded_stage_re_schedules_next(monkeypatch: pytest.MonkeyPatch):
    handoff = AsyncMock()
    monkeypatch.setattr(
        "audit_workbench.services.run.processor.schedule_next_agent_stage",
        handoff,
    )
    monkeypatch.setattr(
        "audit_workbench.services.run.processor.resolve_recipe",
        lambda _settings: SimpleNamespace(
            is_ok=True,
            value=SimpleNamespace(agents=(AgentId.IDP, AgentId.FRAUD)),
        ),
    )
    monkeypatch.setattr(
        "audit_workbench.services.run.processor.get_settings",
        lambda: SimpleNamespace(),
    )

    run = SimpleNamespace(
        id="run-1",
        status="running",
        run_metadata=None,
        last_activity_at=None,
        workflow_id="wf-1",
        worker_pool="extract",
    )
    record_agent_outcome(
        run,  # type: ignore[arg-type]
        AgentOutcome(
            agent=AgentId.FRAUD,
            status=AgentStatus.SKIPPED,
            payload=FraudOutcome(run_id="run-1", summary="skipped"),
        ),
    )
    session = AsyncMock()
    session.flush = AsyncMock()
    # Final stage already recorded but no pendingCompletion → finalize raises; catch via mock.
    monkeypatch.setattr(
        "audit_workbench.services.run.processor.finalize_pending_completion",
        AsyncMock(),
    )

    handled = await _resume_after_recorded_stage(
        session, run, AgentId.FRAUD, request_id="r1"  # type: ignore[arg-type]
    )
    assert handled is True
    handoff.assert_not_awaited()


@pytest.mark.asyncio
async def test_resume_after_recorded_idp_hands_off_to_fraud(monkeypatch: pytest.MonkeyPatch):
    handoff = AsyncMock()
    monkeypatch.setattr(
        "audit_workbench.services.run.processor.schedule_next_agent_stage",
        handoff,
    )
    monkeypatch.setattr(
        "audit_workbench.services.run.processor.resolve_recipe",
        lambda _settings: SimpleNamespace(
            is_ok=True,
            value=SimpleNamespace(agents=(AgentId.IDP, AgentId.FRAUD)),
        ),
    )
    monkeypatch.setattr(
        "audit_workbench.services.run.processor.get_settings",
        lambda: SimpleNamespace(),
    )

    from audit_workbench.agents.idp.contracts import ExtractionOutput, IdpOutcome, ValidationOutput

    run = SimpleNamespace(
        id="run-1",
        status="running",
        run_metadata=None,
        last_activity_at=None,
        workflow_id="wf-1",
        worker_pool="extract",
    )
    record_agent_outcome(
        run,  # type: ignore[arg-type]
        AgentOutcome(
            agent=AgentId.IDP,
            status=AgentStatus.PASSED,
            payload=IdpOutcome(
                run_id="run-1",
                workflow_id="wf-1",
                extraction=ExtractionOutput(by_document=()),
                validation=ValidationOutput(
                    rule_results=(),
                    overall_status="passed",
                    summary_passed=0,
                    summary_failed=0,
                ),
            ),
        ),
    )
    session = AsyncMock()
    session.flush = AsyncMock()

    handled = await _resume_after_recorded_stage(
        session, run, AgentId.IDP, request_id="r1"  # type: ignore[arg-type]
    )
    assert handled is True
    handoff.assert_awaited_once()
    assert handoff.await_args.args[2] is AgentId.FRAUD
