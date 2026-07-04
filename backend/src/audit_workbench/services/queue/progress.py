"""Queue position updates on run progress (DB + SSE)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.models import Run, RunStatus
from audit_workbench.services.queue.position import apply_queue_meta, queue_position
from audit_workbench.services.run_events import publish_run_progress
from audit_workbench.services.run.progress_persist import init_queued_progress


async def init_queued_progress_with_position(session: AsyncSession, run_id: str) -> None:
    await init_queued_progress(session, run_id)
    run = await session.get(Run, run_id)
    if not run or not run.progress:
        return
    position, depth = await queue_position(session, run_id)
    if position is None or depth is None:
        return
    run.progress = apply_queue_meta(run.progress, position=position, depth=depth)


async def refresh_queued_positions(session: AsyncSession) -> int:
    """Update queue position metadata for all queued runs (DB + SSE)."""
    result = await session.execute(
        select(Run)
        .where(Run.status == RunStatus.queued.value)
        .order_by(Run.created_at.asc(), Run.id.asc())
    )
    runs = list(result.scalars())
    depth = len(runs)
    if depth == 0:
        return 0

    updated = 0
    for index, run in enumerate(runs, start=1):
        if not run.progress:
            continue
        progress = apply_queue_meta(run.progress, position=index, depth=depth)
        if progress == run.progress:
            continue
        run.progress = progress
        updated += 1
        await publish_run_progress(run.id, progress)
    if updated:
        await session.flush()
    return updated


async def enrich_progress_for_poll(session: AsyncSession, run: Run) -> dict | None:
    """Refresh queue position on poll while the run is still queued."""
    if not run.progress:
        return None
    if run.status != RunStatus.queued.value:
        return run.progress
    position, depth = await queue_position(session, run.id)
    if position is None or depth is None:
        return run.progress
    progress = apply_queue_meta(run.progress, position=position, depth=depth)
    if progress != run.progress:
        run.progress = progress
        await session.flush()
    return progress
