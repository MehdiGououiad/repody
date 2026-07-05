from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from audit_workbench.services.run.domain.entity import DomainRunStatus, RunEntity
from audit_workbench.services.run.domain.errors import InvalidRunTransition
from audit_workbench.services.run.domain.events import (
    RunCompleted,
    RunDomainEvent,
    RunFailed,
    RunQueued,
    RunStarted,
)

_TERMINAL = frozenset({DomainRunStatus.done, DomainRunStatus.failed})


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

    status: DomainRunStatus
    started_at: datetime
    finished_at: None
    error: None
    overall_status: None
    summary_total: int
    summary_passed: int
    summary_failed: int
    fields_extracted: int
    run_metadata: None


class RunLifecycle:
    """Aggregate root — enterprise rules only; no ORM or infrastructure."""

    def __init__(self, entity: RunEntity) -> None:
        self._entity = entity
        self._events: list[RunDomainEvent] = []

    @property
    def entity(self) -> RunEntity:
        return self._entity

    @property
    def run_id(self) -> str:
        return self._entity.id

    @property
    def status(self) -> DomainRunStatus:
        return self._entity.status

    def is_terminal(self) -> bool:
        return self._entity.status in _TERMINAL

    @staticmethod
    def start_field_updates(now: datetime) -> RunStartFieldUpdates:
        return RunStartFieldUpdates(
            status=DomainRunStatus.running,
            started_at=now,
            finished_at=None,
            error=None,
            overall_status=None,
            summary_total=0,
            summary_passed=0,
            summary_failed=0,
            fields_extracted=0,
            run_metadata=None,
        )

    @classmethod
    def record_queued(
        cls,
        entity: RunEntity,
        *,
        occurred_at: datetime,
    ) -> tuple[RunLifecycle, RunQueued]:
        lifecycle = cls(entity)
        event = RunQueued(
            run_id=entity.id,
            occurred_at=occurred_at,
            workflow_id=entity.workflow_id,
            source=entity.source,
            worker_pool=entity.worker_pool,
        )
        lifecycle._events.append(event)
        return lifecycle, event

    def _apply_start_fields(self, updates: RunStartFieldUpdates) -> None:
        self._entity.status = updates.status
        self._entity.started_at = updates.started_at
        self._entity.finished_at = updates.finished_at
        self._entity.error = updates.error
        self._entity.overall_status = updates.overall_status
        self._entity.summary_total = updates.summary_total
        self._entity.summary_passed = updates.summary_passed
        self._entity.summary_failed = updates.summary_failed
        self._entity.fields_extracted = updates.fields_extracted
        self._entity.run_metadata = updates.run_metadata

    def apply_started(self, now: datetime) -> RunStarted:
        if self._entity.status != DomainRunStatus.queued:
            raise InvalidRunTransition(
                self._entity.id,
                self._entity.status.value,
                "start",
            )
        self._apply_start_fields(self.start_field_updates(now))
        return self._emit_started(now)

    def record_claimed(self, now: datetime) -> RunStarted:
        """Emit RunStarted after an atomic CAS claim already applied start fields."""
        if self._entity.status != DomainRunStatus.running:
            raise InvalidRunTransition(
                self._entity.id,
                self._entity.status.value,
                "record_claimed",
            )
        return self._emit_started(now)

    def _emit_started(self, now: datetime) -> RunStarted:
        event = RunStarted(
            run_id=self._entity.id,
            occurred_at=now,
            workflow_id=self._entity.workflow_id,
        )
        self._events.append(event)
        return event

    def complete(self, outcome: RunCompletionOutcome, now: datetime) -> RunCompleted:
        if self._entity.status != DomainRunStatus.running:
            raise InvalidRunTransition(
                self._entity.id,
                self._entity.status.value,
                "complete",
            )
        self._entity.status = DomainRunStatus.done
        self._entity.overall_status = outcome.overall_status
        self._entity.summary_total = outcome.summary_total
        self._entity.summary_passed = outcome.summary_passed
        self._entity.summary_failed = outcome.summary_failed
        self._entity.fields_extracted = outcome.fields_extracted
        self._entity.finished_at = now
        self._entity.run_metadata = outcome.run_metadata
        if outcome.progress is not None:
            self._entity.progress = outcome.progress
        event = RunCompleted(
            run_id=self._entity.id,
            occurred_at=now,
            overall_status=outcome.overall_status,
            summary_total=outcome.summary_total,
            summary_passed=outcome.summary_passed,
            summary_failed=outcome.summary_failed,
        )
        self._events.append(event)
        return event

    def fail(
        self,
        error: str,
        now: datetime,
        *,
        expected_status: DomainRunStatus | None = None,
    ) -> RunFailed | None:
        if self.is_terminal():
            return None
        if expected_status is not None and self._entity.status != expected_status:
            return None
        previous_status = self._entity.status.value
        message = error[:4000]
        self._entity.status = DomainRunStatus.failed
        self._entity.error = message
        self._entity.finished_at = now
        event = RunFailed(
            run_id=self._entity.id,
            occurred_at=now,
            error=message,
            previous_status=previous_status,
        )
        self._events.append(event)
        return event

    def collect_events(self) -> list[RunDomainEvent]:
        return list(self._events)
