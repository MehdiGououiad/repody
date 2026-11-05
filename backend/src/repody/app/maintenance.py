"""Periodic upkeep on the API: fail runs that are stuck, resend tasks that were never sent.

Every API replica runs the loop; a Redis key lets one of them do the work each interval."""

from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select

from repody.app.runs import fail_run
from repody.infra import db, queue
from repody.infra.models import Run
from repody.infra.redis import get_redis
from repody.settings import get_settings

log = structlog.get_logger(__name__)

QUEUED_LIMIT = timedelta(hours=1)


async def fail_stuck_runs() -> int:
    """A run still ``running`` past its timeout lost its worker; one queued for an hour
    will not start."""
    now = datetime.now(UTC)
    running_limit = timedelta(minutes=get_settings().run_timeout_minutes + 1)
    async with db.session_factory() as session:
        running = list(
            await session.scalars(
                select(Run.id).where(Run.status == "running", Run.started_at < now - running_limit)
            )
        )
        queued = list(
            await session.scalars(
                select(Run.id).where(Run.status == "queued", Run.created_at < now - QUEUED_LIMIT)
            )
        )
    for run_id in running:
        await fail_run(run_id, "The worker stopped before the run finished.", only_if="running")
    for run_id in queued:
        await fail_run(run_id, "The run waited over an hour for a worker.", only_if="queued")
    return len(running) + len(queued)


async def _claim_turn(interval: int) -> bool:
    """One API replica does the upkeep per interval: the first to set the key."""
    return bool(await get_redis().set("repody:maintenance", "1", nx=True, ex=interval))


async def _upkeep() -> None:
    failed = await fail_stuck_runs()
    resent = await queue.redispatch_lost()
    if failed or resent:
        log.info("maintenance", runs_failed=failed, runs_resent=resent)


async def run_forever(stop: asyncio.Event) -> None:
    interval = get_settings().maintenance_interval_seconds
    while not stop.is_set():
        try:
            if await _claim_turn(interval):
                await _upkeep()
        except Exception:
            log.exception("maintenance_failed")
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=interval)
