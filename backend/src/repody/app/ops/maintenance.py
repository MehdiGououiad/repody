"""Background maintenance: stale run recovery, re-sending undispatched runs, queue refresh."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from repody.app.queue.progress import refresh_queued_positions
from repody.app.run.dispatch import redispatch_undispatched
from repody.app.run.state import fail_run
from repody.infra.db import base as db_base
from repody.infra.db.models import Run, RunStatus
from repody.settings import get_settings

log = structlog.get_logger()


def _stale_running_message(minutes: int) -> str:
    return (
        f"Run exceeded {minutes} minute worker timeout (stale running state — retry the test run)"
    )


def _stale_queued_message(minutes: int) -> str:
    return (
        f"Run stayed queued for over {minutes} minutes (dispatch may have failed — retry the run)"
    )


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
        if await fail_run(
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
        if await fail_run(
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


async def reap_stale_runs(*, session: AsyncSession | None = None) -> int:
    """Mark long-running or stuck-queued jobs as failed so the UI does not hang forever."""
    settings = get_settings()
    running_minutes = settings.stale_run_timeout_minutes
    queued_minutes = settings.queued_stale_timeout_minutes

    if session is not None:
        running = await _reap_stale_running_runs(session, minutes=running_minutes)
        queued = await _reap_stale_queued_runs(session, minutes=queued_minutes)
        return running + queued

    async with db_base.async_session_factory() as owned:
        running = await _reap_stale_running_runs(owned, minutes=running_minutes)
        queued = await _reap_stale_queued_runs(owned, minutes=queued_minutes)
        return running + queued


async def run_maintenance_cycle() -> None:
    """One pass: stale runs, re-send undispatched runs, queue head refresh."""
    reaped = await reap_stale_runs()
    async with db_base.async_session_factory() as session:
        redispatched = await redispatch_undispatched(session)
        await refresh_queued_positions(session)
        await session.commit()
    if reaped or redispatched:
        log.info(
            "maintenance_cycle_done",
            stale_runs_reaped=reaped,
            runs_redispatched=redispatched,
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
