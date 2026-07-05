from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass(frozen=True, kw_only=True)
class RunDomainEvent:
    """Base domain event for the Run aggregate (Audit Execution context)."""

    event_id: str = field(default_factory=lambda: uuid4().hex)
    run_id: str
    occurred_at: datetime


@dataclass(frozen=True, kw_only=True)
class RunQueued(RunDomainEvent):
    workflow_id: str
    source: str
    worker_pool: str | None = None


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


RunDomainEventUnion = RunQueued | RunStarted | RunCompleted | RunFailed
