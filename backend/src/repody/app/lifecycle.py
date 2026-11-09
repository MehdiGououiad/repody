"""Run and workflow lifecycles: the states, and the only code that changes them.

Run::

    queued ──claim (worker)──▶ running ──finish (worker)──▶ done
       │                          │
       └──fail (start error, ─────┴──fail (error, timeout,──▶ failed
           queued > 1 h)              worker lost)

    done and failed are final. ``outcome`` (passed | warning | failed) exists only when done.

Workflow::

    draft ──deploy──▶ active ──deploy (new API key)──▶ active
      └──────────────archive───────────────────────▶ archived (final, hidden)

    The server owns a workflow's status: saving the definition never changes it, deploying
    makes it active, deleting archives it. Active means deployed (``deployed_at`` is set).

Every run transition is one conditional UPDATE (``WHERE status IN <allowed sources>``), so two
processes racing on one run (a duplicate task delivery, maintenance and a slow worker) cannot
both move it: the loser's update matches no row. The database CHECK constraints (infra/models.py,
alembic/versions) reject any state these transitions would not produce. Diagrams: docs/LIFECYCLES.md.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from repody.infra.models import Run
from repody.schemas.run import RunStatus

RUN_TRANSITIONS: dict[RunStatus, tuple[RunStatus, ...]] = {
    "queued": ("running", "failed"),
    "running": ("done", "failed"),
    "done": (),
    "failed": (),
}


def run_sources(to: RunStatus) -> list[RunStatus]:
    """The states a run can move to ``to`` from."""
    return [source for source, targets in RUN_TRANSITIONS.items() if to in targets]


async def move_run(
    session: AsyncSession,
    run_id: str,
    to: RunStatus,
    *,
    only_from: RunStatus | None = None,
    **values: Any,
) -> bool:
    """Move the run to ``to`` (setting ``values`` too) if it is in a state allowed to; False
    when it is not (already moved by another process). The caller commits."""
    sources = run_sources(to)
    if only_from is not None:
        if only_from not in sources:
            raise ValueError(f"A run cannot go from {only_from} to {to}.")
        sources = [only_from]
    moved = await session.execute(
        update(Run)
        .where(Run.id == run_id, Run.status.in_(sources))
        .values(status=to, **values)
        .returning(Run.id)
    )
    return moved.scalar_one_or_none() is not None
