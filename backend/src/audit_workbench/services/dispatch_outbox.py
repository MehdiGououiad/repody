"""Durable Hatchet dispatch outbox — replay after API commit."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.models import RunDispatchOutbox
from audit_workbench.services.run_dispatch import mark_run_dispatch_failed
from audit_workbench.settings import get_settings

log = structlog.get_logger(__name__)

_STATUS_PENDING = "pending"
_STATUS_DONE = "dispatched"
_STATUS_FAILED = "failed"

_dispatch_tasks: set[asyncio.Task[None]] = set()


def _is_transient_dispatch_error(exc: Exception) -> bool:
    """True when Hatchet dispatch may succeed on a later attempt."""
    msg = str(exc).lower()
    transient_markers = (
        "connection",
        "timeout",
        "temporarily",
        "unavailable",
        "503",
        "502",
        "504",
        "refused",
        "reset by peer",
        "broken pipe",
    )
    return any(marker in msg for marker in transient_markers)


async def enqueue_dispatch(
    session: AsyncSession,
    *,
    run_id: str,
    pool: str,
    workflow_id: str,
    request_id: str | None,
) -> None:
    session.add(
        RunDispatchOutbox(
            run_id=run_id,
            pool=pool,
            workflow_id=workflow_id,
            request_id=request_id,
            status=_STATUS_PENDING,
            dispatch_attempts=0,
        )
    )
    await session.flush()


async def dispatch_outbox_row(session: AsyncSession, row: RunDispatchOutbox) -> bool:
    """Attempt Hatchet dispatch for one outbox row. Returns True on success."""
    from audit_workbench.services.run_dispatch import dispatch_audit_run

    settings = get_settings()
    row.dispatch_attempts = int(row.dispatch_attempts or 0) + 1
    await session.flush()

    try:
        await dispatch_audit_run(
            row.run_id,
            pool=row.pool,
            workflow_id=row.workflow_id,
            request_id=row.request_id,
        )
    except Exception as exc:
        transient = _is_transient_dispatch_error(exc)
        attempts = row.dispatch_attempts
        if transient and attempts < settings.dispatch_max_attempts:
            row.status = _STATUS_PENDING
            row.error = str(exc)[:2000]
            await session.flush()
            log.warning(
                "dispatch_outbox_retry_scheduled",
                run_id=row.run_id,
                attempts=attempts,
                max_attempts=settings.dispatch_max_attempts,
                error=str(exc),
            )
            return False

        row.status = _STATUS_FAILED
        row.error = str(exc)[:2000]
        await session.flush()
        await mark_run_dispatch_failed(row.run_id, exc)
        log.warning(
            "dispatch_outbox_failed",
            run_id=row.run_id,
            attempts=attempts,
            error=str(exc),
        )
        return False

    row.status = _STATUS_DONE
    row.dispatched_at = datetime.now(UTC)
    row.error = None
    await session.flush()
    return True


async def dispatch_outbox_run(run_id: str) -> bool:
    """Dispatch one outbox row in a dedicated session (background / maintenance)."""
    from audit_workbench.db.base import async_session_factory
    from audit_workbench.services.admission import refresh_queued_positions

    async with async_session_factory() as session:
        row = await session.get(RunDispatchOutbox, run_id)
        if row is None:
            return False
        ok = await dispatch_outbox_row(session, row)
        await refresh_queued_positions(session)
        await session.commit()
        return ok


def schedule_outbox_dispatch(run_id: str) -> None:
    """Fire-and-forget Hatchet dispatch after the API transaction commits."""

    async def _run() -> None:
        try:
            await dispatch_outbox_run(run_id)
        except Exception:
            log.exception("background_dispatch_failed", run_id=run_id)

    task = asyncio.create_task(_run(), name=f"dispatch-{run_id}")
    _dispatch_tasks.add(task)
    task.add_done_callback(_dispatch_tasks.discard)


async def drain_dispatch_tasks() -> None:
    """Await in-flight background dispatches (API shutdown / test teardown)."""
    pending = list(_dispatch_tasks)
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)


async def replay_dispatch_outbox(session: AsyncSession, *, limit: int = 50) -> int:
    """Retry pending rows and transient failures under the attempt budget."""
    settings = get_settings()
    max_attempts = settings.dispatch_max_attempts
    result = await session.execute(
        select(RunDispatchOutbox)
        .where(
            or_(
                RunDispatchOutbox.status == _STATUS_PENDING,
                (
                    (RunDispatchOutbox.status == _STATUS_FAILED)
                    & (RunDispatchOutbox.dispatch_attempts < max_attempts)
                ),
            )
        )
        .order_by(RunDispatchOutbox.created_at.asc())
        .limit(limit)
    )
    rows = list(result.scalars())
    dispatched = 0
    for row in rows:
        if row.status == _STATUS_FAILED:
            row.status = _STATUS_PENDING
            await session.flush()
        if await dispatch_outbox_row(session, row):
            dispatched += 1
    return dispatched


# Backwards-compatible alias for maintenance imports.
replay_pending_dispatches = replay_dispatch_outbox
