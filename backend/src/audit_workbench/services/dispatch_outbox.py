"""Durable Taskiq dispatch outbox — claim/commit then kiq (no lock across Redis)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.models import RunDispatchOutbox
from audit_workbench.services.run.dispatch import mark_run_dispatch_failed
from audit_workbench.settings import get_settings

log = structlog.get_logger(__name__)

_STATUS_PENDING = "pending"
_STATUS_DISPATCHING = "dispatching"
_STATUS_DONE = "dispatched"
_STATUS_FAILED = "failed"

_dispatch_tasks: set[asyncio.Task[None]] = set()


@dataclass(frozen=True, slots=True)
class _ClaimedDispatch:
    run_id: str
    pool: str
    workflow_id: str
    request_id: str | None
    agent_stage: str
    attempts: int


def _is_transient_dispatch_error(exc: Exception) -> bool:
    """True when Taskiq dispatch may succeed on a later attempt."""
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


def _supports_skip_locked(session: AsyncSession) -> bool:
    bind = session.get_bind()
    return bind.dialect.name == "postgresql"


async def enqueue_dispatch(
    session: AsyncSession,
    *,
    run_id: str,
    pool: str,
    workflow_id: str,
    request_id: str | None,
    agent_stage: str = "idp",
) -> None:
    session.add(
        RunDispatchOutbox(
            run_id=run_id,
            pool=pool,
            agent_stage=agent_stage,
            workflow_id=workflow_id,
            request_id=request_id,
            status=_STATUS_PENDING,
            dispatch_attempts=0,
        )
    )
    await session.flush()


async def _claim_outbox_row(
    session: AsyncSession, row: RunDispatchOutbox
) -> _ClaimedDispatch | None:
    """Mark row dispatching and return payload. Caller must commit to release the lock."""
    if row.status == _STATUS_DONE:
        return None
    row.dispatch_attempts = int(row.dispatch_attempts or 0) + 1
    row.status = _STATUS_DISPATCHING
    row.error = None
    await session.flush()
    return _ClaimedDispatch(
        run_id=row.run_id,
        pool=row.pool,
        workflow_id=row.workflow_id,
        request_id=row.request_id,
        agent_stage=getattr(row, "agent_stage", None) or "idp",
        attempts=row.dispatch_attempts,
    )


async def _finalize_dispatch_success(run_id: str) -> None:
    from audit_workbench.db.base import async_session_factory

    async with async_session_factory() as session:
        row = await session.get(RunDispatchOutbox, run_id)
        if row is None:
            return
        row.status = _STATUS_DONE
        row.dispatched_at = datetime.now(UTC)
        row.error = None
        await session.commit()


async def _finalize_dispatch_failure(claimed: _ClaimedDispatch, exc: Exception) -> bool:
    """Persist retry/fail. Returns False (not successfully dispatched)."""
    from audit_workbench.db.base import async_session_factory

    settings = get_settings()
    transient = _is_transient_dispatch_error(exc)
    async with async_session_factory() as session:
        row = await session.get(RunDispatchOutbox, claimed.run_id)
        if row is None:
            return False
        attempts = int(row.dispatch_attempts or claimed.attempts)
        if transient and attempts < settings.dispatch_max_attempts:
            row.status = _STATUS_PENDING
            row.error = str(exc)[:2000]
            await session.commit()
            log.warning(
                "dispatch_outbox_retry_scheduled",
                run_id=claimed.run_id,
                attempts=attempts,
                max_attempts=settings.dispatch_max_attempts,
                error=str(exc),
            )
            return False

        row.status = _STATUS_FAILED
        row.error = str(exc)[:2000]
        await session.commit()
        await mark_run_dispatch_failed(claimed.run_id, exc)
        log.warning(
            "dispatch_outbox_failed",
            run_id=claimed.run_id,
            attempts=attempts,
            error=str(exc),
        )
        return False


async def _kiq_claimed(claimed: _ClaimedDispatch) -> bool:
    """Dispatch outside any DB lock/transaction."""
    from audit_workbench.services.run.dispatch import dispatch_audit_run

    try:
        await dispatch_audit_run(
            claimed.run_id,
            pool=claimed.pool,
            workflow_id=claimed.workflow_id,
            request_id=claimed.request_id,
            agent_stage=claimed.agent_stage,
        )
    except Exception as exc:
        return await _finalize_dispatch_failure(claimed, exc)

    await _finalize_dispatch_success(claimed.run_id)
    return True


async def dispatch_outbox_row(session: AsyncSession, row: RunDispatchOutbox) -> bool:
    """Claim row (caller holds lock), commit elsewhere, then kiq.

    Prefer ``dispatch_outbox_run`` / ``replay_dispatch_outbox`` which commit before Redis.
    This helper claims in ``session``; caller must ``commit`` before awaiting the returned
    work — use ``claim_and_dispatch_outbox_row`` for the safe pattern.
    """
    claimed = await _claim_outbox_row(session, row)
    if claimed is None:
        return True
    await session.commit()
    return await _kiq_claimed(claimed)


async def dispatch_outbox_run(run_id: str) -> bool:
    """Claim one outbox row, commit (release lock), then Taskiq kiq."""
    from audit_workbench.db.base import async_session_factory

    claimed: _ClaimedDispatch | None = None
    async with async_session_factory() as session:
        stmt = select(RunDispatchOutbox).where(RunDispatchOutbox.run_id == run_id)
        if _supports_skip_locked(session):
            stmt = stmt.with_for_update(skip_locked=True)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return False
        if row.status == _STATUS_DONE:
            return True
        # Crash recovery: allow reclaim of stuck dispatching rows.
        if row.status == _STATUS_DISPATCHING:
            row.status = _STATUS_PENDING
            await session.flush()
        claimed = await _claim_outbox_row(session, row)
        await session.commit()

    if claimed is None:
        return True
    return await _kiq_claimed(claimed)


def schedule_outbox_dispatch(run_id: str) -> None:
    """Fire-and-forget Taskiq dispatch after the API transaction commits."""

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
    if not pending:
        return
    try:
        await asyncio.wait_for(
            asyncio.gather(*pending, return_exceptions=True),
            timeout=15.0,
        )
    except TimeoutError:
        log.warning(
            "drain_dispatch_tasks_timeout",
            pending=len(pending),
        )
        for task in pending:
            if not task.done():
                task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)


async def replay_dispatch_outbox(session: AsyncSession, *, limit: int | None = None) -> int:
    """Claim pending/failed rows, commit to release locks, then kiq outside the lock.

    ``session`` is used only for the claim batch; Redis work uses dedicated sessions.
    Kiq calls run concurrently up to ``dispatch_kiq_concurrency``.
    """
    settings = get_settings()
    max_attempts = settings.dispatch_max_attempts
    batch_limit = int(limit if limit is not None else settings.dispatch_replay_batch_size)
    stmt = (
        select(RunDispatchOutbox)
        .where(
            or_(
                RunDispatchOutbox.status == _STATUS_PENDING,
                RunDispatchOutbox.status == _STATUS_DISPATCHING,
                (
                    (RunDispatchOutbox.status == _STATUS_FAILED)
                    & (RunDispatchOutbox.dispatch_attempts < max_attempts)
                ),
            )
        )
        .order_by(RunDispatchOutbox.created_at.asc())
        .limit(batch_limit)
    )
    if _supports_skip_locked(session):
        stmt = stmt.with_for_update(skip_locked=True)
    result = await session.execute(stmt)
    rows = list(result.scalars())
    claimed_list: list[_ClaimedDispatch] = []
    for row in rows:
        if row.status == _STATUS_FAILED or row.status == _STATUS_DISPATCHING:
            row.status = _STATUS_PENDING
            await session.flush()
        claimed = await _claim_outbox_row(session, row)
        if claimed is not None:
            claimed_list.append(claimed)
    await session.commit()

    if not claimed_list:
        return 0

    sem = asyncio.Semaphore(max(1, int(settings.dispatch_kiq_concurrency)))

    async def _kiq_one(claimed: _ClaimedDispatch) -> bool:
        async with sem:
            return await _kiq_claimed(claimed)

    results = await asyncio.gather(*(_kiq_one(c) for c in claimed_list))
    return sum(1 for ok in results if ok)


async def purge_dispatched_outbox(session: AsyncSession) -> int:
    """Delete old successfully-dispatched outbox rows (table hygiene)."""
    days = max(1, int(get_settings().outbox_retain_dispatched_days))
    cutoff = datetime.now(UTC) - timedelta(days=days)
    result = await session.execute(
        delete(RunDispatchOutbox).where(
            RunDispatchOutbox.status == _STATUS_DONE,
            RunDispatchOutbox.dispatched_at.is_not(None),
            RunDispatchOutbox.dispatched_at < cutoff,
        )
    )
    deleted = int(result.rowcount or 0)
    if deleted:
        log.info("outbox_dispatched_purged", count=deleted, older_than_days=days)
    return deleted
