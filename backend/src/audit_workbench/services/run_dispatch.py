"""Dispatch audit runs to Taskiq workers."""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.models import RunStatus
from audit_workbench.services.run_pool_classifier import resolve_worker_pool
from audit_workbench.services.run_terminal import (
    PUBLIC_DISPATCH_FAILURE_MESSAGE,
    fail_run_terminal,
)
from audit_workbench.settings import get_settings
from audit_workbench.taskiq.broker import startup_taskiq_brokers
from audit_workbench.taskiq.models import AuditRunInput
from audit_workbench.taskiq.tasks import get_process_audit_run_task

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
) -> str:
    """Enqueue the audit-run task after the API transaction commits."""
    settings = get_settings()
    if pool is None:
        if session is None:
            from audit_workbench.db.base import async_session_factory

            async with async_session_factory() as owned:
                pool = await resolve_worker_pool(owned, run_id)
        else:
            pool = await resolve_worker_pool(session, run_id)

    await startup_taskiq_brokers()
    task = get_process_audit_run_task(pool)
    await task.kiq(
        AuditRunInput(
            run_id=run_id,
            extract_pool=pool,
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
        queue_name=f"repody:audit:{pool}",
        redis_url=settings.redis_url.split("@")[-1],
    )
    return run_id


async def close_taskiq_brokers() -> None:
    from audit_workbench.taskiq.broker import shutdown_taskiq_brokers

    await shutdown_taskiq_brokers()
