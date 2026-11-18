"""Run and workflow lifecycles: the states, and the only code that changes them.

Run::

    queued ──claim (worker)──▶ running ──finish (worker)──▶ done
       │                          │
       └──fail (start error, ─────┴──fail (error, timeout,──▶ failed
           queued > 1 h)              cancelled)

    done and failed are final. ``outcome`` (passed | warning | failed) exists only when done.
    A running run whose worker died stays running: Hatchet gives its task to another worker,
    which starts it over (repody.app.execute._claim). The maintenance cron fails the runs the
    queue lost (``fail_stuck``).

Workflow::

    draft ──deploy──▶ active ──deploy (new API key)──▶ active
      └──────────────archive───────────────────────▶ archived (final, hidden)

    The server owns a workflow's status: saving the definition never changes it, deploying
    makes it active, deleting archives it. Active means deployed (``deployed_at`` is set).

Every run transition is one conditional UPDATE (``WHERE status IN <allowed sources>``), so two
processes racing on one run (a duplicate task delivery, maintenance and a slow worker) cannot
both move it: the loser's update matches no row. The database CHECK constraints (infra/models.py)
reject any state these transitions would not produce. Diagrams: docs/LIFECYCLES.md.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import ColumnElement, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from repody.app import credits
from repody.infra import db
from repody.infra.models import Run
from repody.schemas.run import RunStatus
from repody.settings import get_settings

log = structlog.get_logger(__name__)

QUEUE_TIMEOUT = timedelta(hours=1)  # a run that waits longer for a worker fails (Hatchet)
# How long past Hatchet's own limits the maintenance sweep waits before failing a run Hatchet
# never reported (fail_stuck): a worker that is restarting gets its tasks back well within it.
STUCK_MARGIN = timedelta(minutes=10)
STUCK = (
    "The run was lost by the queue: it was never started, or its worker stopped. Start it again."
)

RUN_TRANSITIONS: dict[RunStatus, tuple[RunStatus, ...]] = {
    "queued": ("running", "failed"),
    "running": ("done", "failed"),
    "done": (),
    "failed": (),
}


def run_sources(to: RunStatus) -> list[RunStatus]:
    """The states a run can move to ``to`` from."""
    return [source for source, targets in RUN_TRANSITIONS.items() if to in targets]


async def move_runs(
    session: AsyncSession,
    to: RunStatus,
    *where: ColumnElement[bool],
    only_from: RunStatus | None = None,
    **values: Any,
) -> list[str]:
    """Move the runs matching ``where`` that are in a state allowed to go to ``to`` (setting
    ``values`` too); the ids of the runs moved. The caller commits."""
    sources = run_sources(to)
    if only_from is not None:
        if only_from not in sources:
            raise ValueError(f"A run cannot go from {only_from} to {to}.")
        sources = [only_from]
    moved = await session.scalars(
        update(Run)
        .where(Run.status.in_(sources), *where)
        .values(status=to, **values)
        .returning(Run.id)
    )
    return list(moved)


async def move_run(
    session: AsyncSession,
    run_id: str,
    to: RunStatus,
    *,
    only_from: RunStatus | None = None,
    **values: Any,
) -> bool:
    """Move one run (see ``move_runs``); False when it is not in a state allowed to (already
    moved by another process)."""
    return bool(await move_runs(session, to, Run.id == run_id, only_from=only_from, **values))


def failure(error: str) -> dict[str, Any]:
    return {"error": error, "finished_at": datetime.now(UTC)}


async def fail(
    session: AsyncSession, run_id: str, error: str, *, only_from: RunStatus | None = None
) -> bool:
    """Move a queued or running run to failed and settle its credits (repody.app.credits);
    False when it was not in such a state. The caller commits."""
    if not await move_run(session, run_id, "failed", only_from=only_from, **failure(error)):
        return False
    await credits.settle_failed(session, run_id)
    return True


async def fail_run(run_id: str, error: str, *, only_if: RunStatus | None = None) -> bool:
    """Mark a queued or running run failed (``only_if`` narrows the expected status)."""
    async with db.session_factory() as session:
        failed = await fail(session, run_id, error, only_from=only_if)
        await session.commit()
    if failed:
        log.warning("run_failed", run_id=run_id, error=error)
    return failed


async def fail_stuck() -> int:
    """Fail the runs Hatchet will never report on: queued past QUEUE_TIMEOUT (it never got the
    task: the API stopped between saving the run and queueing it), or running past the run
    timeout (the task was lost with Hatchet's history). Each is settled like any failure: a
    run that never started pays nothing. Run by the maintenance cron; the count failed."""
    now = datetime.now(UTC)
    timeout = timedelta(minutes=get_settings().run_timeout_minutes)
    async with db.session_factory() as session:
        ids = list(
            await session.scalars(
                select(Run.id).where(
                    (
                        (Run.status == "queued")
                        & (Run.created_at < now - QUEUE_TIMEOUT - STUCK_MARGIN)
                    )
                    | ((Run.status == "running") & (Run.started_at < now - timeout - STUCK_MARGIN))
                )
            )
        )
    failed = 0
    for run_id in ids:
        failed += await fail_run(run_id, STUCK)
    return failed
