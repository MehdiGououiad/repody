from __future__ import annotations

import json

import structlog

from audit_workbench.services.operator_job_model import OperatorJob

log = structlog.get_logger()
_REDIS_JOB_PREFIX = "audit:operator:job:"
_REDIS_JOB_ORDER = "audit:operator:job_order"


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
