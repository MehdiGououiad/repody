"""Background maintenance: stale run recovery."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.base import async_session_factory
from audit_workbench.db.models import Run, RunStatus
from audit_workbench.services.run.terminal import fail_run_terminal
from audit_workbench.settings import get_settings

log = structlog.get_logger()


def _stale_running_message(minutes: int) -> str:
    return (
        f"Run exceeded {minutes} minute worker timeout "
        "(stale running state — retry the test run)"
    )


def _stale_queued_message(minutes: int) -> str:
    return (
        f"Run stayed queued for over {minutes} minutes "
        "(dispatch may have failed — retry the run)"
    )


def _running_activity_at(run: Run) -> datetime | None:
    """Prefer last_activity_at so multi-stage handoffs do not look stuck on started_at."""
    return run.last_activity_at or run.started_at


async def _worker_backlog_active(session: AsyncSession) -> bool:
    """True when at least one run is actively executing on a worker."""
    result = await session.execute(
        select(Run.id).where(Run.status == RunStatus.running.value).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _reap_stale_running_runs(session: AsyncSession, *, minutes: int) -> int:
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)
    # Activity clock: COALESCE(last_activity_at, started_at) so handoffs refresh the lease.
    activity = func.coalesce(Run.last_activity_at, Run.started_at)
    stale_ids = (
        (
            await session.execute(
                select(Run.id).where(
                    Run.status == RunStatus.running.value,
                    activity.is_not(None),
                    activity < cutoff,
                )
            )
        )
        .scalars()
        .all()
    )
    reaped = 0
    for run_id in stale_ids:
        if await fail_run_terminal(
            run_id,
            _stale_running_message(minutes),
            session=session,
            expected_status=RunStatus.running.value,
        ):
            reaped += 1
    if reaped:
        log.warning(
            "stale_running_runs_reaped",
            count=reaped,
            run_ids=list(stale_ids),
            timeout_minutes=minutes,
        )
    return reaped


async def _reap_stale_queued_runs(session: AsyncSession, *, minutes: int) -> int:
    if await _worker_backlog_active(session):
        return 0
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)
    stale_ids = (
        (
            await session.execute(
                select(Run.id).where(
                    Run.status == RunStatus.queued.value,
                    Run.created_at.is_not(None),
                    Run.created_at < cutoff,
                )
            )
        )
        .scalars()
        .all()
    )
    reaped = 0
    for run_id in stale_ids:
        if await fail_run_terminal(
            run_id,
            _stale_queued_message(minutes),
            session=session,
            expected_status=RunStatus.queued.value,
        ):
            reaped += 1
    if reaped:
        log.warning(
            "stale_queued_runs_reaped",
            count=reaped,
            run_ids=list(stale_ids),
            timeout_minutes=minutes,
        )
    return reaped


async def maybe_reap_stale_run(session: AsyncSession, run: Run) -> bool:
    """Fail a single run when it exceeded queued/running stale thresholds."""
    settings = get_settings()
    now = datetime.now(UTC)
    activity_at = _running_activity_at(run)
    if run.status == RunStatus.running.value and activity_at:
        cutoff = now - timedelta(minutes=settings.stale_run_timeout_minutes)
        if activity_at < cutoff:
            return await fail_run_terminal(
                run.id,
                _stale_running_message(settings.stale_run_timeout_minutes),
                session=session,
                expected_status=RunStatus.running.value,
            )
    if run.status == RunStatus.queued.value and run.created_at:
        if await _worker_backlog_active(session):
            return False
        cutoff = now - timedelta(minutes=settings.queued_stale_timeout_minutes)
        if run.created_at < cutoff:
            return await fail_run_terminal(
                run.id,
                _stale_queued_message(settings.queued_stale_timeout_minutes),
                session=session,
                expected_status=RunStatus.queued.value,
            )
    return False


async def reap_stale_runs(*, session: AsyncSession | None = None) -> int:
    """Mark long-running or stuck-queued jobs as failed so the UI does not hang forever."""
    settings = get_settings()
    running_minutes = settings.stale_run_timeout_minutes
    queued_minutes = settings.queued_stale_timeout_minutes

    if session is not None:
        running = await _reap_stale_running_runs(session, minutes=running_minutes)
        queued = await _reap_stale_queued_runs(session, minutes=queued_minutes)
        return running + queued

    async with async_session_factory() as owned:
        running = await _reap_stale_running_runs(owned, minutes=running_minutes)
        queued = await _reap_stale_queued_runs(owned, minutes=queued_minutes)
        return running + queued


async def run_maintenance_cycle() -> None:
    """One pass: stale runs, outbox replay, queue head refresh, outbox purge."""
    reaped = await reap_stale_runs()
    replayed = 0
    purged = 0
    from audit_workbench.services.dispatch_outbox import (
        purge_dispatched_outbox,
        replay_dispatch_outbox,
    )
    from audit_workbench.services.queue import refresh_queued_positions

    async with async_session_factory() as session:
        replayed = await replay_dispatch_outbox(session)
        await refresh_queued_positions(session)
        purged = await purge_dispatched_outbox(session)
        await session.commit()
    if reaped or replayed or purged:
        log.info(
            "maintenance_cycle_done",
            stale_runs_reaped=reaped,
            dispatches_replayed=replayed,
            outbox_purged=purged,
        )


async def maintenance_loop(stop: asyncio.Event) -> None:
    """Periodic maintenance until stop is set."""
    settings = get_settings()
    interval = max(5, settings.maintenance_interval_seconds)
    log.info("maintenance_loop_started", interval_seconds=interval)
    while not stop.is_set():
        try:
            await run_maintenance_cycle()
        except Exception:
            log.exception("maintenance_cycle_failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except TimeoutError:
            continue
    log.info("maintenance_loop_stopped")
