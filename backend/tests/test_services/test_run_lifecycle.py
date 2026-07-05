from __future__ import annotations

from datetime import UTC, datetime

import pytest

from audit_workbench.services.run.domain.entity import DomainRunStatus, RunEntity
from audit_workbench.services.run.domain.errors import InvalidRunTransition
from audit_workbench.services.run.domain.events import RunCompleted, RunFailed, RunStarted
from audit_workbench.services.run.domain.lifecycle import RunCompletionOutcome, RunLifecycle


def _entity(*, status: DomainRunStatus = DomainRunStatus.queued) -> RunEntity:
    return RunEntity(
        id="run-1",
        workflow_id="wf-1",
        source="test",
        status=status,
    )


def test_start_field_updates_resets_execution_fields() -> None:
    now = datetime.now(UTC)
    updates = RunLifecycle.start_field_updates(now)
    assert updates.status == DomainRunStatus.running
    assert updates.started_at == now
    assert updates.finished_at is None
    assert updates.summary_total == 0


def test_apply_started_emits_run_started() -> None:
    entity = _entity()
    now = datetime.now(UTC)
    lifecycle = RunLifecycle(entity)
    event = lifecycle.apply_started(now)
    assert entity.status == DomainRunStatus.running
    assert isinstance(event, RunStarted)
    assert event.run_id == "run-1"
    assert event.workflow_id == "wf-1"


def test_apply_started_rejects_non_queued() -> None:
    entity = _entity(status=DomainRunStatus.running)
    lifecycle = RunLifecycle(entity)
    with pytest.raises(InvalidRunTransition):
        lifecycle.apply_started(datetime.now(UTC))


def test_record_claimed_emits_run_started() -> None:
    entity = _entity(status=DomainRunStatus.running)
    now = datetime.now(UTC)
    lifecycle = RunLifecycle(entity)
    event = lifecycle.record_claimed(now)
    assert isinstance(event, RunStarted)
    assert event.run_id == "run-1"
    assert event.workflow_id == "wf-1"


def test_record_claimed_rejects_non_running() -> None:
    entity = _entity()
    lifecycle = RunLifecycle(entity)
    with pytest.raises(InvalidRunTransition):
        lifecycle.record_claimed(datetime.now(UTC))


def test_complete_emits_run_completed() -> None:
    entity = _entity(status=DomainRunStatus.running)
    entity.started_at = datetime.now(UTC)
    lifecycle = RunLifecycle(entity)
    now = datetime.now(UTC)
    outcome = RunCompletionOutcome(
        overall_status="passed",
        summary_total=2,
        summary_passed=2,
        summary_failed=0,
        fields_extracted=5,
        run_metadata={"durationMs": 100},
        progress=None,
    )
    event = lifecycle.complete(outcome, now)
    assert entity.status == DomainRunStatus.done
    assert entity.overall_status == "passed"
    assert isinstance(event, RunCompleted)
    assert event.summary_total == 2


def test_complete_rejects_non_running() -> None:
    entity = _entity()
    lifecycle = RunLifecycle(entity)
    with pytest.raises(InvalidRunTransition):
        lifecycle.complete(
            RunCompletionOutcome(
                overall_status="passed",
                summary_total=0,
                summary_passed=0,
                summary_failed=0,
                fields_extracted=0,
                run_metadata={},
                progress=None,
            ),
            datetime.now(UTC),
        )


def test_fail_from_running_emits_run_failed() -> None:
    entity = _entity(status=DomainRunStatus.running)
    lifecycle = RunLifecycle(entity)
    now = datetime.now(UTC)
    event = lifecycle.fail("boom", now)
    assert event is not None
    assert entity.status == DomainRunStatus.failed
    assert entity.error == "boom"
    assert isinstance(event, RunFailed)
    assert event.previous_status == DomainRunStatus.running.value


def test_fail_skips_terminal_and_expected_status() -> None:
    done = _entity(status=DomainRunStatus.done)
    assert RunLifecycle(done).fail("late", datetime.now(UTC)) is None

    queued = _entity()
    assert (
        RunLifecycle(queued).fail(
            "wrong",
            datetime.now(UTC),
            expected_status=DomainRunStatus.running,
        )
        is None
    )


def test_fail_truncates_error_message() -> None:
    entity = _entity(status=DomainRunStatus.running)
    lifecycle = RunLifecycle(entity)
    long_error = "x" * 5000
    event = lifecycle.fail(long_error, datetime.now(UTC))
    assert event is not None
    assert len(entity.error or "") == 4000
