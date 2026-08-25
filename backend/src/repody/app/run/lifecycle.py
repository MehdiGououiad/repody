from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from repody.runtime.contracts.result import AppError, ErrorCode, Result
from repody.runtime.run.status import RunStatus

__all__ = ["RunEntity", "RunStatus"]


@dataclass
class RunEntity:
    """Enterprise entity for audit run lifecycle — no framework or persistence imports."""

    id: str
    workflow_id: str
    source: str
    status: RunStatus
    worker_pool: str | None = None
    overall_status: str | None = None
    error: str | None = None
    summary_total: int = 0
    summary_passed: int = 0
    summary_failed: int = 0
    fields_extracted: int = 0
    started_at: datetime | None = None
    last_activity_at: datetime | None = None
    finished_at: datetime | None = None
    run_metadata: dict[str, Any] | None = None
    progress: dict[str, Any] | None = None


@dataclass(frozen=True, kw_only=True)
class RunDomainEvent:
    """Base domain event for the Run aggregate (Audit Execution context)."""

    event_id: str = field(default_factory=lambda: uuid4().hex)
    run_id: str
    occurred_at: datetime


@dataclass(frozen=True, kw_only=True)
class RunStarted(RunDomainEvent):
    workflow_id: str


@dataclass(frozen=True, kw_only=True)
class RunCompleted(RunDomainEvent):
    overall_status: str
    summary_total: int
    summary_passed: int
    summary_failed: int


@dataclass(frozen=True, kw_only=True)
class RunFailed(RunDomainEvent):
    error: str
    previous_status: str


RunDomainEventUnion = RunStarted | RunCompleted | RunFailed

"""Run lifecycle transitions as pure functions (no aggregate class)."""

_TERMINAL = frozenset({RunStatus.done, RunStatus.failed})


@dataclass(frozen=True)
class RunCompletionOutcome:
    overall_status: str
    summary_total: int
    summary_passed: int
    summary_failed: int
    fields_extracted: int
    run_metadata: dict[str, Any]
    progress: dict[str, Any] | None


@dataclass(frozen=True)
class RunStartFieldUpdates:
    """Field values applied when a queued run starts — persistence maps these to columns."""

    status: RunStatus
    started_at: datetime
    last_activity_at: datetime
    finished_at: None
    error: None
    overall_status: None
    summary_total: int
    summary_passed: int
    summary_failed: int
    fields_extracted: int
    run_metadata: None


def is_terminal(entity: RunEntity) -> bool:
    return entity.status in _TERMINAL


def start_field_updates(now: datetime) -> RunStartFieldUpdates:
    return RunStartFieldUpdates(
        status=RunStatus.running,
        started_at=now,
        last_activity_at=now,
        finished_at=None,
        error=None,
        overall_status=None,
        summary_total=0,
        summary_passed=0,
        summary_failed=0,
        fields_extracted=0,
        run_metadata=None,
    )


def _emit_started(entity: RunEntity, now: datetime) -> RunStarted:
    return RunStarted(
        run_id=entity.id,
        occurred_at=now,
        workflow_id=entity.workflow_id,
    )


def _transition_error(run_id: str, status: str, action: str) -> AppError:
    return AppError(
        code=ErrorCode.CONFLICT,
        message=f"Invalid run transition: cannot {action} from status {status} (run {run_id})",
    )


def record_claimed(entity: RunEntity, now: datetime) -> Result[RunStarted]:
    """Emit RunStarted after an atomic CAS claim already applied start fields."""
    if entity.status != RunStatus.running:
        return Result.fail(_transition_error(entity.id, entity.status.value, "record_claimed"))
    return Result.ok(_emit_started(entity, now))


def complete_run_entity(
    entity: RunEntity,
    outcome: RunCompletionOutcome,
    now: datetime,
) -> Result[tuple[RunEntity, RunCompleted]]:
    if entity.status != RunStatus.running:
        return Result.fail(_transition_error(entity.id, entity.status.value, "complete"))
    entity.status = RunStatus.done
    entity.overall_status = outcome.overall_status
    entity.summary_total = outcome.summary_total
    entity.summary_passed = outcome.summary_passed
    entity.summary_failed = outcome.summary_failed
    entity.fields_extracted = outcome.fields_extracted
    entity.finished_at = now
    entity.run_metadata = outcome.run_metadata
    if outcome.progress is not None:
        entity.progress = outcome.progress
    event = RunCompleted(
        run_id=entity.id,
        occurred_at=now,
        overall_status=outcome.overall_status,
        summary_total=outcome.summary_total,
        summary_passed=outcome.summary_passed,
        summary_failed=outcome.summary_failed,
    )
    return Result.ok((entity, event))


def fail_run_entity(
    entity: RunEntity,
    error: str,
    now: datetime,
    *,
    expected_status: RunStatus | None = None,
) -> tuple[RunEntity, RunFailed] | None:
    if is_terminal(entity):
        return None
    if expected_status is not None and entity.status != expected_status:
        return None
    previous_status = entity.status.value
    message = error[:4000]
    entity.status = RunStatus.failed
    entity.error = message
    entity.finished_at = now
    event = RunFailed(
        run_id=entity.id,
        occurred_at=now,
        error=message,
        previous_status=previous_status,
    )
    return entity, event
