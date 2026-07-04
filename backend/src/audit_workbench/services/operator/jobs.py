from __future__ import annotations

import asyncio
import json
import uuid
from collections import deque
from collections.abc import Awaitable, Callable
from pathlib import Path

import structlog

from audit_workbench.services.operator.job_model import OperatorJob, utc_now

log = structlog.get_logger()
MAX_JOBS = 30
MAX_OUTPUT_CHARS = 24_000
_REDIS_JOB_PREFIX = "audit:operator:job:"
_REDIS_JOB_ORDER = "audit:operator:job_order"

_jobs: dict[str, OperatorJob] = {}
_job_order: deque[str] = deque()
_tasks: set[asyncio.Task[None]] = set()
_persist_tasks: set[asyncio.Task[None]] = set()
JobRunner = Callable[[OperatorJob], Awaitable[None]]


async def persist_operator_job(job: OperatorJob, *, max_jobs: int) -> None:
    from audit_workbench.services.redis_pool import get_redis

    try:
        client = await get_redis()
        key = f"{_REDIS_JOB_PREFIX}{job.id}"
        await client.set(key, json.dumps(job.to_store()))
        await client.zadd(_REDIS_JOB_ORDER, {job.id: job.created_at.timestamp()})
        count = await client.zcard(_REDIS_JOB_ORDER)
        if count <= max_jobs:
            return

        stale_ids = await client.zrange(_REDIS_JOB_ORDER, 0, count - max_jobs - 1)
        if not stale_ids:
            return
        await client.zrem(_REDIS_JOB_ORDER, *stale_ids)
        await client.delete(*(f"{_REDIS_JOB_PREFIX}{job_id}" for job_id in stale_ids))
    except Exception as exc:
        log.debug("operator_job_redis_persist_skipped", job_id=job.id, error=str(exc))


async def delete_operator_job(job_id: str) -> None:
    from audit_workbench.services.redis_pool import get_redis

    try:
        client = await get_redis()
        await client.delete(f"{_REDIS_JOB_PREFIX}{job_id}")
        await client.zrem(_REDIS_JOB_ORDER, job_id)
    except Exception as exc:
        log.debug("operator_job_redis_delete_skipped", job_id=job_id, error=str(exc))


async def load_recent_operator_jobs(
    *,
    max_jobs: int,
    existing_ids: set[str],
) -> list[OperatorJob]:
    from audit_workbench.services.redis_pool import get_redis

    jobs: list[OperatorJob] = []
    try:
        client = await get_redis()
        job_ids = await client.zrevrange(_REDIS_JOB_ORDER, 0, max_jobs - 1)
        for job_id in job_ids:
            if job_id in existing_ids:
                continue
            raw = await client.get(f"{_REDIS_JOB_PREFIX}{job_id}")
            if not raw:
                continue
            try:
                jobs.append(OperatorJob.from_store(json.loads(raw)))
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
    except Exception as exc:
        log.debug("operator_job_redis_hydrate_skipped", error=str(exc))
    return jobs


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
