"""Run state transitions as single conditional UPDATEs (the database enforces the state machine).

queued -> running (claim) -> done (complete) | failed (fail, from any non-terminal state).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from repody.app.run.progress import fail_run_progress
from repody.app.run.sse import publish_run_terminal
from repody.infra.db import base as db_base
from repody.infra.db.models import Run, RunStatus

log = structlog.get_logger(__name__)

PUBLIC_RUN_FAILURE_MESSAGE = "Run failed during processing. Check worker logs for details."
_MAX_ERROR_CHARS = 4000
_TERMINAL = (RunStatus.done.value, RunStatus.failed.value)


async def claim_run(session: AsyncSession, run_id: str, *, now: datetime) -> str | None:
    """queued -> running and reset execution fields; returns the workflow id, or None."""
    claimed = await session.execute(
        update(Run)
        .where(Run.id == run_id, Run.status == RunStatus.queued.value)
        .values(
            status=RunStatus.running.value,
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
        .returning(Run.workflow_id)
    )
    workflow_id = claimed.scalar_one_or_none()
    if workflow_id is not None:
        log.info("run_started", event_domain="audit_run", run_id=run_id, workflow_id=workflow_id)
    return workflow_id


async def complete_run(
    session: AsyncSession,
    run_id: str,
    *,
    overall_status: str,
    summary_total: int,
    summary_passed: int,
    summary_failed: int,
    fields_extracted: int,
    run_metadata: dict[str, Any],
    progress: dict[str, Any] | None,
) -> bool:
    """running -> done, commit, then tell SSE subscribers. False if the run left `running`."""
    done = await session.execute(
        update(Run)
        .where(Run.id == run_id, Run.status == RunStatus.running.value)
        .values(
            status=RunStatus.done.value,
            overall_status=overall_status,
            summary_total=summary_total,
            summary_passed=summary_passed,
            summary_failed=summary_failed,
            fields_extracted=fields_extracted,
            run_metadata=run_metadata,
            progress=progress,
            finished_at=datetime.now(UTC),
        )
        .returning(Run.id)
    )
    if done.scalar_one_or_none() is None:
        await session.rollback()
        return False
    await session.commit()
    await publish_run_terminal(run_id, status=RunStatus.done.value)
    log.info(
        "run_completed",
        event_domain="audit_run",
        run_id=run_id,
        overall_status=overall_status,
        summary_total=summary_total,
        summary_failed=summary_failed,
    )
    return True


async def fail_run(
    run_id: str,
    error: str,
    *,
    session: AsyncSession | None = None,
    expected_status: str | None = None,
) -> bool:
    """Non-terminal (or exactly `expected_status`) -> failed; publishes a terminal snapshot."""

    async def _fail(owned: AsyncSession) -> bool:
        condition = (
            Run.status == expected_status
            if expected_status is not None
            else Run.status.not_in(_TERMINAL)
        )
        message = error[:_MAX_ERROR_CHARS]
        failed = await owned.execute(
            update(Run)
            .where(Run.id == run_id, condition)
            .values(status=RunStatus.failed.value, error=message, finished_at=datetime.now(UTC))
            .returning(Run.id)
        )
        if failed.scalar_one_or_none() is None:
            await owned.rollback()
            return False
        await owned.commit()
        await fail_run_progress(run_id, message)
        log.warning(
            "run_failed_terminal", event_domain="audit_run", run_id=run_id, error=message[:200]
        )
        return True

    if session is not None:
        return await _fail(session)
    async with db_base.async_session_factory() as owned:
        return await _fail(owned)
