from __future__ import annotations

import asyncio
import json
import sys
import uuid
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger()
MAX_JOBS = 30
MAX_OUTPUT_CHARS = 24_000
_REDIS_JOB_PREFIX = "audit:operator:job:"
_REDIS_JOB_ORDER = "audit:operator:job_order"


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class OperatorJob:
    id: str
    kind: str
    label: str
    status: str = "queued"
    created_at: datetime = field(default_factory=_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    progress: str = ""
    output: str = ""
    error: str | None = None
    report_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "status": self.status,
            "createdAt": self.created_at.isoformat(),
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "output": self.output,
            "error": self.error,
            "hasReport": bool(self.report_path),
        }

    def to_store(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "output": self.output,
            "error": self.error,
            "report_path": self.report_path,
        }

    @classmethod
    def from_store(cls, payload: dict[str, Any]) -> OperatorJob:
        def _parse_dt(value: str | None) -> datetime | None:
            if not value:
                return None
            return datetime.fromisoformat(value)

        return cls(
            id=str(payload["id"]),
            kind=str(payload["kind"]),
            label=str(payload["label"]),
            status=str(payload.get("status", "queued")),
            created_at=_parse_dt(payload.get("created_at")) or _now(),
            started_at=_parse_dt(payload.get("started_at")),
            completed_at=_parse_dt(payload.get("completed_at")),
            progress=str(payload.get("progress", "")),
            output=str(payload.get("output", "")),
            error=payload.get("error"),
            report_path=payload.get("report_path"),
        )


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


async def _persist_job(job: OperatorJob) -> None:
    from audit_workbench.services.redis_pool import get_redis

    try:
        client = await get_redis()
        key = f"{_REDIS_JOB_PREFIX}{job.id}"
        await client.set(key, json.dumps(job.to_store()))
        await client.zadd(_REDIS_JOB_ORDER, {job.id: job.created_at.timestamp()})
        count = await client.zcard(_REDIS_JOB_ORDER)
        if count > MAX_JOBS:
            stale_ids = await client.zrange(_REDIS_JOB_ORDER, 0, count - MAX_JOBS - 1)
            if stale_ids:
                await client.zrem(_REDIS_JOB_ORDER, *stale_ids)
                if stale_ids:
                    await client.delete(*(f"{_REDIS_JOB_PREFIX}{job_id}" for job_id in stale_ids))
    except Exception as exc:
        log.debug("operator_job_redis_persist_skipped", job_id=job.id, error=str(exc))


async def _delete_job_redis(job_id: str) -> None:
    from audit_workbench.services.redis_pool import get_redis

    try:
        client = await get_redis()
        await client.delete(f"{_REDIS_JOB_PREFIX}{job_id}")
        await client.zrem(_REDIS_JOB_ORDER, job_id)
    except Exception as exc:
        log.debug("operator_job_redis_delete_skipped", job_id=job_id, error=str(exc))


def _schedule_persist(job: OperatorJob) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    async def _run() -> None:
        await _persist_job(job)

    task = loop.create_task(_run(), name=f"operator-persist-{job.id}")
    _persist_tasks.add(task)
    task.add_done_callback(_persist_tasks.discard)


def _schedule_redis_delete(job_id: str) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    task = loop.create_task(_delete_job_redis(job_id), name=f"operator-delete-{job_id}")
    _persist_tasks.add(task)
    task.add_done_callback(_persist_tasks.discard)


async def hydrate_operator_jobs_from_redis() -> None:
    """Restore recent operator jobs after API restart (best-effort)."""
    from audit_workbench.services.redis_pool import get_redis

    try:
        client = await get_redis()
        job_ids = await client.zrevrange(_REDIS_JOB_ORDER, 0, MAX_JOBS - 1)
        for job_id in job_ids:
            if job_id in _jobs:
                continue
            raw = await client.get(f"{_REDIS_JOB_PREFIX}{job_id}")
            if not raw:
                continue
            try:
                job = OperatorJob.from_store(json.loads(raw))
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
            _register_job(job)
    except Exception as exc:
        log.debug("operator_job_redis_hydrate_skipped", error=str(exc))


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
        job.started_at = _now()
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
            job.completed_at = _now()
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


def benchmark_command(
    *,
    document: Path,
    manifest: Path,
    output_dir: Path,
    profile: str,
    models: list[str],
    validation_mode: str,
    warm_runs: int,
    minimum_accuracy: float,
    cache_check: bool,
) -> list[str]:
    command = [
        sys.executable,
        "/app/scripts/benchmark_suite.py",
        "--api",
        "http://127.0.0.1:8000",
        "--document",
        str(document),
        "--manifest",
        str(manifest),
        "--output-dir",
        str(output_dir),
        "--profile",
        profile,
        "--model-validation",
        validation_mode,
        "--warm-runs",
        str(warm_runs),
        "--minimum-accuracy",
        str(minimum_accuracy),
        "--timeout-seconds",
        "900",
        "--continue-on-failure",
        "--cache-check" if cache_check else "--no-cache-check",
    ]
    for model in models:
        command.extend(["--model", model])
    return command


def load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
