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

from audit_workbench.infra.db import base as db_base
from audit_workbench.infra.db.models import Run
from audit_workbench.infra.db.models.enums import RunStatus as DbRunStatus
from audit_workbench.runtime.agent_metadata import (
    clear_pending_completion,
    pending_completion_from_run,
)
from audit_workbench.runtime.contracts.result import AppError, ErrorCode, Result
from audit_workbench.app.run.lifecycle import (
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
from audit_workbench.app.run.persistence import (
    bind_commit,
    bind_load,
    bind_save,
)
from audit_workbench.app.run.progress import fail_run_progress

log = structlog.get_logger(__name__)

PUBLIC_RUN_FAILURE_MESSAGE = (
    "Run failed while processing. Contact an operator with the run id for details."
)
PUBLIC_DISPATCH_FAILURE_MESSAGE = (
    "Run dispatch failed. Retry the run or contact an operator."
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


# --- Domain event side effects ---


async def _on_run_started(event: RunStarted) -> None:
    # Do not refresh all queued positions here — that is O(N) DB + SSE and
    # dominated claim latency under deep queues. Pollers recompute position
    # with O(1) SQL; maintenance periodically reconciles progress rows.
    log.info(
        "run_started",
        event_domain="audit_run",
        run_id=event.run_id,
        workflow_id=event.workflow_id,
    )


async def _on_run_completed(event: RunCompleted) -> None:
    from audit_workbench.app.run.sse import publish_run_terminal

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
        return await fail_run(
            request,
            load=bind_load(owned),
            save=bind_save(owned),
            commit=bind_commit(owned),
            publish=publish_run_domain_events,
        )

    if session is not None:
        return await _execute(session)

    async with db_base.async_session_factory() as owned_session:
        return await _execute(owned_session)


async def finalize_pending_completion(session: AsyncSession, run: Run) -> None:
    """Complete a run from ``run_metadata.pendingCompletion`` (final non-IDP stage)."""
    pending = pending_completion_from_run(run)
    if pending is None:
        raise RuntimeError(f"missing pendingCompletion for run {run.id}")
    # pending.run_metadata is timing/summary only — keep agentOutcomes written after IDP.
    merged_meta = dict(pending.run_metadata)
    current = run.run_metadata if isinstance(run.run_metadata, dict) else {}
    outcomes = current.get("agentOutcomes")
    if isinstance(outcomes, dict) and outcomes:
        merged_meta["agentOutcomes"] = outcomes
    clear_pending_completion(run)
    await session.flush()
    completed = await complete_run(
        CompleteRunRequest(
            run_id=run.id,
            outcome=RunCompletionOutcome(
                overall_status=pending.overall_status,
                summary_total=pending.summary_total,
                summary_passed=pending.summary_passed,
                summary_failed=pending.summary_failed,
                fields_extracted=pending.fields_extracted,
                run_metadata=merged_meta,
                progress=pending.progress,
            ),
        ),
        load=bind_load(session),
        save=bind_save(session),
        commit=bind_commit(session),
        publish=publish_run_domain_events,
        now=datetime.now(UTC),
    )
    if not completed.is_ok:
        err = completed.error
        raise RuntimeError(err.message if err else "complete_run failed")
