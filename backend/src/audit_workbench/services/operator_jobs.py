from __future__ import annotations

import asyncio
import uuid
from collections import deque
from collections.abc import Awaitable, Callable
from pathlib import Path

import structlog

from audit_workbench.services.operator_job_model import OperatorJob, utc_now
from audit_workbench.services.operator_job_redis import (
    delete_operator_job,
    load_recent_operator_jobs,
    persist_operator_job,
)

log = structlog.get_logger()
MAX_JOBS = 30
MAX_OUTPUT_CHARS = 24_000


_jobs: dict[str, OperatorJob] = {}
_job_order: deque[str] = deque()
_tasks: set[asyncio.Task[None]] = set()
_persist_tasks: set[asyncio.Task[None]] = set()
JobRunner = Callable[[OperatorJob], Awaitable[None]]


def _register_job(job: OperatorJob) -> None:
    _jobs[job.id] = job
    if job.id not in _job_order:
        _job_order.append(job.id)
    while len(_job_order) > MAX_JOBS:
        expired = _job_order.popleft()
        _jobs.pop(expired, None)
        _schedule_redis_delete(expired)


def _schedule_persist(job: OperatorJob) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    async def _run() -> None:
        await persist_operator_job(job, max_jobs=MAX_JOBS)

    task = loop.create_task(_run(), name=f"operator-persist-{job.id}")
    _persist_tasks.add(task)
    task.add_done_callback(_persist_tasks.discard)


def _schedule_redis_delete(job_id: str) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    task = loop.create_task(delete_operator_job(job_id), name=f"operator-delete-{job_id}")
    _persist_tasks.add(task)
    task.add_done_callback(_persist_tasks.discard)


async def hydrate_operator_jobs_from_redis() -> None:
    """Restore recent operator jobs after API restart (best-effort)."""
    for job in await load_recent_operator_jobs(max_jobs=MAX_JOBS, existing_ids=set(_jobs)):
        _register_job(job)


def get_job(job_id: str) -> OperatorJob | None:
    return _jobs.get(job_id)


def list_jobs() -> list[OperatorJob]:
    return [_jobs[job_id] for job_id in reversed(_job_order) if job_id in _jobs]


def append_output(job: OperatorJob, text: str) -> None:
    combined = f"{job.output}{text}"
    job.output = combined[-MAX_OUTPUT_CHARS:]
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines:
        job.progress = lines[-1][-300:]
    _schedule_persist(job)


def create_job(kind: str, label: str, runner: JobRunner) -> OperatorJob:
    job = OperatorJob(id=uuid.uuid4().hex[:12], kind=kind, label=label)
    _register_job(job)
    _schedule_persist(job)

    async def execute() -> None:
        job.status = "running"
        job.started_at = utc_now()
        _schedule_persist(job)
        try:
            await runner(job)
            job.status = "completed"
        except asyncio.CancelledError:
            job.status = "cancelled"
            raise
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            append_output(job, f"\nERROR: {exc}\n")
            log.exception("operator_job_failed", job_id=job.id, kind=job.kind)
        finally:
            job.completed_at = utc_now()
            _schedule_persist(job)

    task = asyncio.create_task(execute(), name=f"operator-{kind}-{job.id}")
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return job


async def run_command(
    job: OperatorJob,
    args: list[str],
    *,
    cwd: Path | None = None,
) -> None:
    process = await asyncio.create_subprocess_exec(
        *args,
        cwd=str(cwd) if cwd else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    assert process.stdout is not None
    while line := await process.stdout.readline():
        append_output(job, line.decode("utf-8", errors="replace"))
    return_code = await process.wait()
    if return_code != 0:
        raise RuntimeError(f"Command exited with status {return_code}")
