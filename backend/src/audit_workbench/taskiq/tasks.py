"""Audit-run Taskiq tasks registered per worker pool queue."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from audit_workbench.settings import get_settings
from audit_workbench.taskiq.broker import get_broker
from audit_workbench.taskiq.models import AuditRunInput

if TYPE_CHECKING:
    from taskiq import AsyncTaskiqDecoratedTask

log = structlog.get_logger(__name__)

_tasks: dict[str, AsyncTaskiqDecoratedTask[Any, Any]] = {}


async def _execute_audit_run(input: AuditRunInput) -> dict[str, str]:
    settings = get_settings()
    run_id = input.run_id
    workflow_id = input.workflow_id
    request_id = input.request_id

    log.info(
        "taskiq_run_started",
        event_domain="audit_run",
        run_id=run_id,
        workflow_id=workflow_id,
        request_id=request_id,
        pool=input.extract_pool,
        timeout_minutes=settings.worker_task_timeout_minutes,
    )
    try:
        from audit_workbench.db.base import async_session_factory
        from audit_workbench.db.models import Run
        from audit_workbench.observability.context import bind_log_context, log_context
        from audit_workbench.observability.tracing import start_span
        from audit_workbench.services.run_processor import execute_run_with_timeout

        async with start_span(
            "process_audit_run",
            {
                "run.id": run_id,
                "workflow.id": workflow_id or "",
                "request.id": request_id or "",
                "worker.pool": input.extract_pool,
            },
        ):
            with log_context(
                run_id=run_id,
                workflow_id=workflow_id,
                request_id=request_id,
                correlation_id=request_id,
                worker_pool=input.extract_pool,
            ):
                async with async_session_factory() as session:
                    if workflow_id is None:
                        run = await session.get(Run, run_id)
                        workflow_id = run.workflow_id if run else None
                        if workflow_id:
                            bind_log_context(workflow_id=workflow_id)
                    await execute_run_with_timeout(session, run_id)
    except Exception as exc:
        from audit_workbench.services.run_terminal import (
            PUBLIC_RUN_FAILURE_MESSAGE,
            fail_run_terminal,
        )

        if isinstance(exc, TimeoutError):
            log.warning(
                "taskiq_run_timed_out",
                run_id=run_id,
                timeout_minutes=settings.worker_task_timeout_minutes,
            )
        else:
            log.exception("taskiq_run_failed", run_id=run_id, error=repr(exc))
        await fail_run_terminal(run_id, PUBLIC_RUN_FAILURE_MESSAGE)
        raise
    log.info("taskiq_run_completed", run_id=run_id, pool=input.extract_pool)
    return {"run_id": run_id, "phase": "done"}


def get_process_audit_run_task(pool: str) -> AsyncTaskiqDecoratedTask[Any, Any]:
    """Return the pool-specific task (registers on first use)."""
    if pool in _tasks:
        return _tasks[pool]

    settings = get_settings()
    broker = get_broker(pool)
    timeout_seconds = max(60, settings.worker_task_timeout_minutes * 60)

    @broker.task(
        task_name="process-audit-run",
        retry_on_error=True,
        max_retries=1,
        timeout=timeout_seconds,
    )
    async def process_audit_run_task(input: AuditRunInput) -> dict[str, str]:
        return await _execute_audit_run(input)

    _tasks[pool] = process_audit_run_task
    return process_audit_run_task


def clear_task_registry() -> None:
    """Reset registered tasks (tests)."""
    _tasks.clear()
