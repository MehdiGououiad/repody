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
both move it: the loser's update matches no row. The database CHECK constraints (infra/models.py)
reject any state these transitions would not produce. Diagrams: docs/LIFECYCLES.md.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import ColumnElement, update
from sqlalchemy.ext.asyncio import AsyncSession

from repody.infra import db
from repody.infra.models import Run
from repody.schemas.run import RunStatus
from repody.settings import get_settings

log = structlog.get_logger(__name__)

RUN_TRANSITIONS: dict[RunStatus, tuple[RunStatus, ...]] = {
    "queued": ("running", "failed"),
    "running": ("done", "failed"),
    "done": (),
    "failed": (),
}
# A running run past its timeout (plus a grace minute for the worker to fail it itself) has
# lost its worker; a queued run this old will not start.
RUNNING_GRACE = timedelta(minutes=1)
QUEUED_LIMIT = timedelta(hours=1)


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


async def fail_run(run_id: str, error: str, *, only_if: RunStatus | None = None) -> bool:
    """Mark a queued or running run failed (``only_if`` narrows the expected status)."""
    async with db.session_factory() as session:
        failed = await move_run(session, run_id, "failed", only_from=only_if, **failure(error))
        await session.commit()
    if failed:
        log.warning("run_failed", run_id=run_id, error=error)
    return failed


def _running_limit() -> timedelta:
    return timedelta(minutes=get_settings().run_timeout_minutes) + RUNNING_GRACE


def stuck_running(now: datetime) -> ColumnElement[bool]:
    """Running runs past their timeout and the grace minute: their worker is gone."""
    return (Run.status == "running") & (Run.started_at < now - _running_limit())


def is_stuck(run: Run, now: datetime) -> bool:
    """The same test as ``stuck_running`` and ``stuck_queued``, on a loaded run."""
    if run.status == "running":
        return run.started_at is not None and run.started_at < now - _running_limit()
    return run.status == "queued" and run.created_at < now - QUEUED_LIMIT


def stuck_queued(now: datetime) -> ColumnElement[bool]:
    return (Run.status == "queued") & (Run.created_at < now - QUEUED_LIMIT)
