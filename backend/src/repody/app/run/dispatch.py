"""Dispatch audit runs to Taskiq workers."""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from repody.app.run.commands import (
    PUBLIC_DISPATCH_FAILURE_MESSAGE,
    fail_run_terminal,
)
from repody.app.run.pool import resolve_worker_pool
from repody.infra.db.models import RunStatus
from repody.runtime.pools import agent_for_pool
from repody.settings import get_settings
from repody.taskiq.broker import startup_taskiq_brokers
from repody.taskiq.models import AuditRunInput
from repody.taskiq.tasks import get_process_audit_run_task

log = structlog.get_logger()


async def mark_run_dispatch_failed(run_id: str, exc: Exception) -> None:
    """Mark a queued run failed when Taskiq dispatch fails after the API commit."""
    await fail_run_terminal(
        run_id,
        PUBLIC_DISPATCH_FAILURE_MESSAGE,
        expected_status=RunStatus.queued.value,
    )
    log.warning(
        "taskiq_dispatch_failed_terminal",
        event_domain="audit_run",
        run_id=run_id,
        error_type=type(exc).__name__,
        error_message=repr(exc),
    )


async def dispatch_audit_run(
    run_id: str,
    *,
    session: AsyncSession | None = None,
    pool: str | None = None,
    workflow_id: str | None = None,
    request_id: str | None = None,
    agent_stage: str | None = None,
) -> str:
    """Enqueue the audit-run task after the API transaction commits."""
    settings = get_settings()
    if pool is None:
        if session is None:
            from repody.infra.db.base import async_session_factory

            async with async_session_factory() as owned:
                pool = await resolve_worker_pool(owned, run_id)
        else:
            pool = await resolve_worker_pool(session, run_id)

    stage = agent_stage or agent_for_pool(pool).value
    await startup_taskiq_brokers()
    task = get_process_audit_run_task(pool)
    await task.kiq(
        AuditRunInput(
            run_id=run_id,
            extract_pool=pool,
            agent_stage=stage,
            workflow_id=workflow_id,
            request_id=request_id,
        )
    )
    log.info(
        "taskiq_run_dispatched",
        event_domain="audit_run",
        run_id=run_id,
        workflow_id=workflow_id,
        request_id=request_id,
        pool=pool,
        agent_stage=stage,
        queue_name=f"repody:audit:{pool}",
        redis_url=settings.redis_url.split("@")[-1],
    )
    return run_id


async def close_taskiq_brokers() -> None:
    from repody.taskiq.broker import shutdown_taskiq_brokers

    await shutdown_taskiq_brokers()
