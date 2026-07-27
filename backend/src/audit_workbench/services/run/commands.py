"""Run lifecycle use cases as plain functions (no use-case classes)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from audit_workbench.platform.contracts.result import AppError, ErrorCode, Result
from audit_workbench.services.run.lifecycle import RunStatus, RunEntity
from audit_workbench.services.run.lifecycle import RunDomainEvent
from audit_workbench.services.run.lifecycle import (
    RunCompletionOutcome,
    complete_run_entity,
    fail_run_entity,
    record_claimed,
)


@dataclass(frozen=True, slots=True)
class FailRunRequest:
    run_id: str
    error: str
    expected_status: RunStatus | None = None


@dataclass(frozen=True, slots=True)
class ClaimRunRequest:
    run_id: str


@dataclass(frozen=True, slots=True)
class ClaimRunResult:
    entity: RunEntity
    events: list[RunDomainEvent]


@dataclass(frozen=True, slots=True)
class CompleteRunRequest:
    run_id: str
    outcome: RunCompletionOutcome


LoadFn = Callable[[str], Awaitable[RunEntity | None]]
SaveFn = Callable[[RunEntity], Awaitable[None]]
CommitFn = Callable[[], Awaitable[None]]
ClaimFn = Callable[[str, datetime], Awaitable[RunEntity | None]]
PublishFn = Callable[[Sequence[RunDomainEvent]], Awaitable[None]]


async def fail_run(
    request: FailRunRequest,
    *,
    load: LoadFn,
    save: SaveFn,
    commit: CommitFn,
    publish: PublishFn,
    now: datetime | None = None,
) -> bool:
    occurred_at = now or datetime.now(UTC)
    entity = await load(request.run_id)
    if entity is None:
        return False
    result = fail_run_entity(
        entity,
        request.error,
        occurred_at,
        expected_status=request.expected_status,
    )
    if result is None:
        return False
    entity, event = result
    await save(entity)
    await commit()
    await publish([event])
    return True


async def claim_run(
    request: ClaimRunRequest,
    *,
    try_claim: ClaimFn,
    now: datetime | None = None,
) -> ClaimRunResult | None:
    occurred_at = now or datetime.now(UTC)
    entity = await try_claim(request.run_id, occurred_at)
    if entity is None:
        return None
    event_r = record_claimed(entity, occurred_at)
    if not event_r.is_ok:
        return None
    return ClaimRunResult(entity=entity, events=[event_r.unwrap()])


async def complete_run(
    request: CompleteRunRequest,
    *,
    load: LoadFn,
    save: SaveFn,
    commit: CommitFn,
    publish: PublishFn,
    now: datetime | None = None,
) -> Result[None]:
    occurred_at = now or datetime.now(UTC)
    entity = await load(request.run_id)
    if entity is None:
        return Result.fail(
            AppError(code=ErrorCode.NOT_FOUND, message=f"Run not found: {request.run_id}")
        )
    completed = complete_run_entity(entity, request.outcome, occurred_at)
    if not completed.is_ok:
        return Result.fail(
            completed.error
            or AppError(code=ErrorCode.CONFLICT, message="Invalid complete transition")
        )
    entity, event = completed.unwrap()
    await save(entity)
    await commit()
    await publish([event])
    return Result.ok(None)
