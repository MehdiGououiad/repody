"""Audit-run Taskiq tasks registered per worker pool queue."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from repody.app.run.commands import PUBLIC_RUN_FAILURE_MESSAGE, fail_run_terminal
from repody.app.run.processor import execute_run_with_timeout
from repody.infra.db import base as db_base
from repody.infra.db.models import Run
from repody.infra.observability.context import bind_log_context, log_context
from repody.settings import get_settings
from repody.taskiq.broker import get_broker
from repody.taskiq.models import AuditRunInput

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
        with log_context(
            run_id=run_id,
            workflow_id=workflow_id,
            request_id=request_id,
            correlation_id=request_id,
            worker_pool=input.extract_pool,
        ):
            if workflow_id is None:
                async with db_base.async_session_factory() as session:
                    run = await session.get(Run, run_id)
                    workflow_id = run.workflow_id if run else None
                    if workflow_id:
                        bind_log_context(workflow_id=workflow_id)
            # No long-lived session across extract HTTP - process_run manages phases.
            await execute_run_with_timeout(run_id, request_id=request_id)
    except Exception as exc:
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
    # execute_run_with_timeout owns the run deadline and marks the run failed; Taskiq's
    # timeout cancels from outside without that handling, so it only backs it up.
    backstop_seconds = max(60, settings.worker_task_timeout_minutes * 60) + 60

    @broker.task(task_name="process-audit-run", timeout=backstop_seconds)
    async def process_audit_run_task(input: AuditRunInput) -> dict[str, str]:
        return await _execute_audit_run(input)

    _tasks[pool] = process_audit_run_task
    return process_audit_run_task


def clear_task_registry() -> None:
    """Reset registered tasks (tests)."""
    _tasks.clear()
