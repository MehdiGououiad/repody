"""Durable Hatchet dispatch outbox — replay after API commit."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.models import RunDispatchOutbox
from audit_workbench.services.run_dispatch import dispatch_audit_run, mark_run_dispatch_failed

log = structlog.get_logger(__name__)

_STATUS_PENDING = "pending"
_STATUS_DONE = "dispatched"
_STATUS_FAILED = "failed"


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
        )
    )
    await session.flush()


async def dispatch_outbox_row(session: AsyncSession, row: RunDispatchOutbox) -> bool:
    """Attempt Hatchet dispatch for one outbox row. Returns True on success."""
    try:
        await dispatch_audit_run(
            row.run_id,
            pool=row.pool,
            workflow_id=row.workflow_id,
            request_id=row.request_id,
        )
    except Exception as exc:
        row.status = _STATUS_FAILED
        row.error = str(exc)[:2000]
        await session.flush()
        await mark_run_dispatch_failed(row.run_id, exc)
        log.warning(
            "dispatch_outbox_failed",
            run_id=row.run_id,
            error=str(exc),
        )
        return False

    row.status = _STATUS_DONE
    row.dispatched_at = datetime.now(UTC)
    row.error = None
    await session.flush()
    return True


async def replay_pending_dispatches(session: AsyncSession, *, limit: int = 50) -> int:
    """Retry pending outbox rows (maintenance sweeper)."""
    result = await session.execute(
        select(RunDispatchOutbox)
        .where(RunDispatchOutbox.status == _STATUS_PENDING)
        .order_by(RunDispatchOutbox.created_at.asc())
        .limit(limit)
    )
    rows = list(result.scalars())
    dispatched = 0
    for row in rows:
        if await dispatch_outbox_row(session, row):
            dispatched += 1
    return dispatched
