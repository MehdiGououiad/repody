"""Queue position updates on run progress (DB + SSE)."""

from __future__ import annotations

import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from repody.infra.db.models import Run, RunStatus
from repody.app.queue.position import apply_queue_meta, queue_position
from repody.app.run.progress import init_queued_progress
from repody.app.run.sse import publish_run_progress
from repody.settings import get_settings


async def init_queued_progress_with_position(session: AsyncSession, run_id: str) -> None:
    await init_queued_progress(session, run_id)
    run = await session.get(Run, run_id)
    if not run or not run.progress:
        return
    position, depth = await queue_position(session, run_id)
    if position is None or depth is None:
        return
    run.progress = apply_queue_meta(run.progress, position=position, depth=depth)


async def refresh_single_queued_run(session: AsyncSession, run_id: str) -> bool:
    """Update one queued run's position/depth (enqueue path — O(1) SQL counts)."""
    run = await session.get(Run, run_id)
    if not run or run.status != RunStatus.queued.value or not run.progress:
        return False
    position, depth = await queue_position(session, run_id)
    if position is None or depth is None:
        return False
    progress = apply_queue_meta(run.progress, position=position, depth=depth)
    if progress == run.progress:
        return False
    run.progress = progress
    await publish_run_progress(run.id, progress)
    await session.flush()
    return True


async def refresh_queued_positions(session: AsyncSession) -> int:
    """Update queue position metadata for the head of the queue (maintenance).

    Caps how many queued rows are loaded/updated per tick so deep queues cannot
    dominate maintenance. Pollers still get live position via O(1) SQL.
    """
    settings = get_settings()
    sse_limit = max(0, int(settings.queue_refresh_sse_limit))
    db_limit = max(sse_limit, int(getattr(settings, "queue_refresh_db_limit", 128)))
    if db_limit <= 0:
        return 0

    depth = int(
        await session.scalar(
            select(func.count()).select_from(Run).where(Run.status == RunStatus.queued.value)
        )
        or 0
    )
    if depth == 0:
        return 0

    result = await session.execute(
        select(Run)
        .options(load_only(Run.id, Run.progress, Run.status, Run.created_at))
        .where(Run.status == RunStatus.queued.value)
        .order_by(Run.created_at.asc(), Run.id.asc())
        .limit(db_limit)
    )
    runs = list(result.scalars())

    updated = 0
    publish_jobs: list[tuple[str, dict]] = []
    for index, run in enumerate(runs, start=1):
        if not run.progress:
            continue
        progress = apply_queue_meta(run.progress, position=index, depth=depth)
        if progress == run.progress:
            continue
        run.progress = progress
        updated += 1
        if index <= sse_limit:
            publish_jobs.append((run.id, progress))
    if updated:
        await session.flush()
    if publish_jobs:
        await asyncio.gather(
            *(publish_run_progress(run_id, progress) for run_id, progress in publish_jobs)
        )
    return updated


async def enrich_progress_for_poll(session: AsyncSession, run: Run) -> dict | None:
    """Compute queue position for poll responses without writing the DB.

    Poll storms must stay read-only; enqueue/maintenance own progress persistence.
    """
    if not run.progress:
        return None
    if run.status != RunStatus.queued.value:
        return run.progress
    position, depth = await queue_position(session, run.id)
    if position is None or depth is None:
        return run.progress
    return apply_queue_meta(run.progress, position=position, depth=depth)
