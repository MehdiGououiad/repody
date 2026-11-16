"""The control room: runs in flight with their live progress, runs that broke, throughput."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from repody.app.dashboard import timing
from repody.app.errors import AppError
from repody.app.lifecycle import failure, move_run
from repody.app.progress import stored
from repody.infra import queue
from repody.infra.models import Run, RunDocument
from repody.schemas.platform import (
    ActiveRun,
    FailedRun,
    HourThroughput,
    Operations,
    QueueCounts,
)

ACTIVE = 25
ERRORS = 10
HOURS = 24


async def get_operations(session: AsyncSession) -> Operations:
    now = datetime.now(UTC)
    since = now - timedelta(hours=HOURS)
    with_files = (
        selectinload(Run.workflow),
        selectinload(Run.documents).load_only(RunDocument.file_name, RunDocument.position),
    )
    active = (
        await session.scalars(
            select(Run)
            .where(Run.status.in_(("queued", "running")))
            .order_by(Run.created_at)
            .limit(ACTIVE)
            .options(*with_files)
        )
    ).all()
    failed = await session.scalars(
        select(Run)
        .where(Run.status == "failed", Run.created_at >= since)
        .order_by(Run.created_at.desc())
        .limit(ERRORS)
        .options(selectinload(Run.workflow))
    )
    queued, running = (
        await session.execute(
            select(
                func.count().filter(Run.status == "queued"),
                func.count().filter(Run.status == "running"),
            )
        )
    ).one()
    hour = func.date_trunc("hour", Run.finished_at)
    per_hour = {
        start: (done, broke)
        for start, done, broke in await session.execute(
            select(
                hour,
                func.count().filter(Run.status == "done"),
                func.count().filter(Run.status == "failed"),
            )
            .where(Run.finished_at >= since)
            .group_by(hour)
        )
    }
    first = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=HOURS - 1)
    hours = [first + timedelta(hours=i) for i in range(HOURS)]
    return Operations(
        queue=QueueCounts(queued_runs=queued, running_runs=running),
        active=[
            ActiveRun(
                id=run.id,
                workflow_id=run.workflow_id,
                workflow_name=run.workflow.name,
                status=run.status,
                source=run.source,
                files=[doc.file_name for doc in run.documents if doc.file_name],
                created_at=run.created_at,
                started_at=run.started_at,
                progress=stored(run),
            )
            for run in active
        ],
        errors=[
            FailedRun(
                id=run.id,
                workflow_id=run.workflow_id,
                workflow_name=run.workflow.name,
                source=run.source,
                error=run.error or "",
                created_at=run.created_at,
            )
            for run in failed
        ],
        throughput=[
            HourThroughput(
                hour=h, done=per_hour.get(h, (0, 0))[0], failed=per_hour.get(h, (0, 0))[1]
            )
            for h in hours
        ],
        timing=await timing(session, since),
    )


async def cancel_run(session: AsyncSession, run_id: str, by: str) -> None:
    """Stop a queued or running run: it fails with who stopped it, and its Hatchet task is
    cancelled. A worker still busy with it cannot finish it (a final state is never overwritten)."""
    if await move_run(session, run_id, "failed", **failure(f"Cancelled by {by}.")):
        await session.commit()
        if task_run_id := await session.scalar(select(Run.task_run_id).where(Run.id == run_id)):
            await queue.cancel(task_run_id)
        return
    # Not moved: unknown, or already finished (perhaps a moment ago, by its worker).
    status = await session.scalar(select(Run.status).where(Run.id == run_id))
    if status is None:
        raise AppError(404, "Run not found.")
    raise AppError(409, f"The run is already {status}.")
