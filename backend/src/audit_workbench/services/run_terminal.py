"""Terminal failure handling for runs (status + progress)."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.models import Run, RunStatus
from audit_workbench.services.run_progress import fail_run_progress

log = structlog.get_logger()

PUBLIC_RUN_FAILURE_MESSAGE = (
    "Run failed while processing. Contact an operator with the run id for details."
)
PUBLIC_DISPATCH_FAILURE_MESSAGE = (
    "Run dispatch failed. Retry the run or contact an operator."
)


async def fail_run_terminal(
    run_id: str,
    error: str,
    *,
    session: AsyncSession | None = None,
    expected_status: str | None = None,
) -> bool:
    """Mark a run failed and publish a terminal progress snapshot for SSE subscribers."""
    message = error[:4000]
    now = datetime.now(UTC)
    updated = False

    async def _apply(db: AsyncSession) -> bool:
        run = await db.get(Run, run_id)
        if not run:
            return False
        if expected_status is not None and run.status != expected_status:
            return False
        if run.status in (RunStatus.done.value, RunStatus.failed.value):
            return False
        run.status = RunStatus.failed.value
        run.error = message
        run.finished_at = now
        await db.commit()
        return True

    if session is not None:
        updated = await _apply(session)
    else:
        from audit_workbench.db.base import async_session_factory

        async with async_session_factory() as owned:
            updated = await _apply(owned)

    if updated:
        await fail_run_progress(run_id, message)
        log.warning("run_failed_terminal", run_id=run_id, error=message[:200])
    return updated
