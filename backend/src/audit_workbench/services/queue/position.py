"""Queue position labels and progress metadata."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.models import Run, RunStatus


async def queue_position(session: AsyncSession, run_id: str) -> tuple[int | None, int | None]:
    """1-based position among queued runs and total queued depth."""
    run = await session.get(Run, run_id)
    if not run or run.status != RunStatus.queued.value:
        return None, None

    result = await session.execute(
        select(Run.id)
        .where(Run.status == RunStatus.queued.value)
        .order_by(Run.created_at.asc(), Run.id.asc())
    )
    ids = list(result.scalars())
    depth = len(ids)
    if depth == 0 or run_id not in ids:
        return None, None
    return ids.index(run_id) + 1, depth


def queue_label(position: int, depth: int) -> str:
    if depth <= 1:
        return "Waiting for worker…"
    return f"Queued — position {position} of {depth}"


def queue_detail(position: int, depth: int) -> str:
    ahead = max(0, position - 1)
    if ahead == 0:
        return "Next in line for a worker slot."
    if ahead == 1:
        return "1 run ahead of you in the queue."
    return f"{ahead} runs ahead of you in the queue."


def apply_queue_meta(progress: dict, *, position: int, depth: int) -> dict:
    """Merge queue position fields into a progress payload."""
    updated = dict(progress)
    updated["queuePosition"] = position
    updated["queueDepth"] = depth
    updated["label"] = queue_label(position, depth)
    steps = list(updated.get("steps") or [])
    if steps and steps[0].get("id") == "queue":
        step0 = dict(steps[0])
        step0["detail"] = queue_detail(position, depth)
        step0["status"] = "active" if position == 1 else "pending"
        steps[0] = step0
    updated["steps"] = steps
    return updated
