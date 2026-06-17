"""Background maintenance: stale run recovery."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.base import async_session_factory
from audit_workbench.db.models import Run, RunStatus
from audit_workbench.services.run_terminal import fail_run_terminal
from audit_workbench.settings import get_settings

log = structlog.get_logger()


async def _worker_backlog_active(session: AsyncSession) -> bool:
    """True when at least one run is actively executing on a worker."""
    result = await session.execute(
        select(Run.id).where(Run.status == RunStatus.running.value).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _reap_stale_running_runs(session: AsyncSession, *, minutes: int) -> int:
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)
    stale_ids = (
        (
            await session.execute(
                select(Run.id).where(
                    Run.status == RunStatus.running.value,
                    Run.started_at.is_not(None),
                    Run.started_at < cutoff,
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
            (
                f"Run exceeded {minutes} minute worker timeout "
                "(stale running state — retry the test run)"
            ),
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
            (
                f"Run stayed queued for over {minutes} minutes "
                "(dispatch may have failed — retry the run)"
            ),
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
    if run.status == RunStatus.running.value and run.started_at:
        cutoff = now - timedelta(minutes=settings.stale_run_timeout_minutes)
        if run.started_at < cutoff:
            return await fail_run_terminal(
                run.id,
                (
                    f"Run exceeded {settings.stale_run_timeout_minutes} minute worker timeout "
                    "(stale running state — retry the test run)"
                ),
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
                (
                    f"Run stayed queued for over {settings.queued_stale_timeout_minutes} minutes "
                    "(dispatch may have failed — retry the run)"
                ),
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
    """One pass: fail stale running and stuck queued jobs; replay dispatch outbox."""
    settings = get_settings()
    reaped = await reap_stale_runs()
    replayed = 0
    from audit_workbench.services.dispatch_outbox import replay_pending_dispatches

    async with async_session_factory() as session:
        replayed = await replay_pending_dispatches(session)
        if settings.admission_control_enabled:
            from audit_workbench.services.admission import refresh_queued_positions

            await refresh_queued_positions(session)
        await session.commit()
    if reaped or replayed:
        log.info("maintenance_cycle_done", stale_runs_reaped=reaped, dispatches_replayed=replayed)


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
