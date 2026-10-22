"""Run lifecycle use cases: claim / complete / fail + side effects.

Pure transitions live in ``lifecycle.py``. This module applies them with
persistence and publishes domain events (SSE / progress).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from repody.app.run.lifecycle import (
    RunCompleted,
    RunCompletionOutcome,
    RunDomainEvent,
    RunEntity,
    RunFailed,
    RunStarted,
    RunStatus,
    complete_run_entity,
    fail_run_entity,
    record_claimed,
)
from repody.app.run.persistence import session_run_ports
from repody.app.run.progress import fail_run_progress
from repody.infra.db import base as db_base
from repody.infra.db.models.enums import RunStatus as DbRunStatus
from repody.runtime.contracts.result import AppError, ErrorCode, Result

log = structlog.get_logger(__name__)

PUBLIC_RUN_FAILURE_MESSAGE = (
    "Run failed while processing. Contact an operator with the run id for details."
)
PUBLIC_DISPATCH_FAILURE_MESSAGE = "Run dispatch failed. Retry the run or contact an operator."


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


# --- Domain event side effects ---


async def _on_run_started(event: RunStarted) -> None:
    # Do not refresh all queued positions here - that is O(N) DB + SSE and
    # dominated claim latency under deep queues. Pollers recompute position
    # with O(1) SQL; maintenance periodically reconciles progress rows.
    log.info(
        "run_started",
        event_domain="audit_run",
        run_id=event.run_id,
        workflow_id=event.workflow_id,
    )


async def _on_run_completed(event: RunCompleted) -> None:
    from repody.app.run.sse import publish_run_terminal

    await publish_run_terminal(event.run_id, status=DbRunStatus.done.value)
    log.info(
        "run_completed",
        event_domain="audit_run",
        run_id=event.run_id,
        overall_status=event.overall_status,
        summary_total=event.summary_total,
        summary_failed=event.summary_failed,
    )


async def _on_run_failed(event: RunFailed) -> None:
    await fail_run_progress(event.run_id, event.error)
    log.warning(
        "run_failed_terminal",
        event_domain="audit_run",
        run_id=event.run_id,
        previous_status=event.previous_status,
        error=event.error[:200],
    )


async def publish_run_domain_events(events: Sequence[RunDomainEvent]) -> None:
    for event in events:
        if isinstance(event, RunStarted):
            await _on_run_started(event)
        elif isinstance(event, RunCompleted):
            await _on_run_completed(event)
        elif isinstance(event, RunFailed):
            await _on_run_failed(event)
        else:
            raise TypeError(f"Unhandled run domain event: {type(event)!r}")


# --- Use cases ---


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


async def fail_run_terminal(
    run_id: str,
    error: str,
    *,
    session: AsyncSession | None = None,
    expected_status: str | None = None,
) -> bool:
    """Mark a run failed and publish a terminal progress snapshot for SSE subscribers."""
    domain_expected = RunStatus(expected_status) if expected_status is not None else None
    request = FailRunRequest(
        run_id=run_id,
        error=error,
        expected_status=domain_expected,
    )

    async def _execute(owned: AsyncSession) -> bool:
        load, save, commit = session_run_ports(owned)
        return await fail_run(
            request,
            load=load,
            save=save,
            commit=commit,
            publish=publish_run_domain_events,
        )

    if session is not None:
        return await _execute(session)

    async with db_base.async_session_factory() as owned_session:
        return await _execute(owned_session)
