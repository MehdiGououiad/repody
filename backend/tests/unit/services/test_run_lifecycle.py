from __future__ import annotations

from datetime import UTC, datetime

from audit_workbench.platform.contracts.result import ErrorCode
from audit_workbench.services.run.lifecycle import RunStatus, RunEntity
from audit_workbench.services.run.lifecycle import RunCompleted, RunFailed, RunStarted
from audit_workbench.services.run.lifecycle import (
    RunCompletionOutcome,
    complete_run_entity,
    fail_run_entity,
    record_claimed,
    start_field_updates,
)


def _entity(*, status: RunStatus = RunStatus.queued) -> RunEntity:
    return RunEntity(
        id="run-1",
        workflow_id="wf-1",
        source="test",
        status=status,
    )


def test_start_field_updates_resets_execution_fields() -> None:
    now = datetime.now(UTC)
    updates = start_field_updates(now)
    assert updates.status == RunStatus.running
    assert updates.started_at == now
    assert updates.last_activity_at == now
    assert updates.finished_at is None
    assert updates.summary_total == 0


def test_record_claimed_emits_run_started() -> None:
    entity = _entity(status=RunStatus.running)
    now = datetime.now(UTC)
    result = record_claimed(entity, now)
    assert result.is_ok
    event = result.unwrap()
    assert isinstance(event, RunStarted)
    assert event.run_id == "run-1"
    assert event.workflow_id == "wf-1"


def test_record_claimed_rejects_non_running() -> None:
    entity = _entity()
    result = record_claimed(entity, datetime.now(UTC))
    assert not result.is_ok
    assert result.error is not None
    assert result.error.code is ErrorCode.CONFLICT


def test_complete_emits_run_completed() -> None:
    entity = _entity(status=RunStatus.running)
    entity.started_at = datetime.now(UTC)
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
    result = complete_run_entity(entity, outcome, now)
    assert result.is_ok
    entity, event = result.unwrap()
    assert entity.status == RunStatus.done
    assert entity.overall_status == "passed"
    assert isinstance(event, RunCompleted)
    assert event.summary_total == 2


def test_complete_rejects_non_running() -> None:
    entity = _entity()
    result = complete_run_entity(
        entity,
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
    assert not result.is_ok
    assert result.error is not None
    assert result.error.code is ErrorCode.CONFLICT


def test_fail_from_running_emits_run_failed() -> None:
    entity = _entity(status=RunStatus.running)
    now = datetime.now(UTC)
    result = fail_run_entity(entity, "boom", now)
    assert result is not None
    entity, event = result
    assert entity.status == RunStatus.failed
    assert entity.error == "boom"
    assert isinstance(event, RunFailed)
    assert event.previous_status == RunStatus.running.value


def test_fail_skips_terminal_and_expected_status() -> None:
    done = _entity(status=RunStatus.done)
    assert fail_run_entity(done, "late", datetime.now(UTC)) is None

    queued = _entity()
    assert (
        fail_run_entity(
            queued,
            "wrong",
            datetime.now(UTC),
            expected_status=RunStatus.running,
        )
        is None
    )


def test_fail_truncates_error_message() -> None:
    entity = _entity(status=RunStatus.running)
    long_error = "x" * 5000
    result = fail_run_entity(entity, long_error, datetime.now(UTC))
    assert result is not None
    entity, _event = result
    assert len(entity.error or "") == 4000
