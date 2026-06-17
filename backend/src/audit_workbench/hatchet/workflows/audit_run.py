from __future__ import annotations

from datetime import timedelta

import structlog
from hatchet_sdk import Context, Hatchet
from hatchet_sdk.labels import DesiredWorkerLabel
from pydantic import BaseModel, Field

from audit_workbench.settings import get_settings

log = structlog.get_logger()

_audit_run_workflow = None


class AuditRunInput(BaseModel):
    run_id: str = Field(description="Primary key of the audit run row.")
    extract_pool: str = Field(default="ocr", description="Worker pool (ocr|fast).")
    workflow_id: str | None = Field(default=None, description="Workflow that owns the run.")
    request_id: str | None = Field(
        default=None,
        description="HTTP correlation / request id from the API enqueue call.",
    )


def register_audit_run_workflow(hatchet: Hatchet):
    settings = get_settings()
    task_timeout = timedelta(minutes=settings.hatchet_task_timeout_minutes)

    workflow = hatchet.workflow(
        name="audit-run",
        input_validator=AuditRunInput,
    )

    @workflow.task(
        name="process-audit-run",
        execution_timeout=task_timeout,
        retries=1,
    )
    async def process_audit_run_task(input: AuditRunInput, ctx: Context) -> dict[str, str]:
        run_id = input.run_id
        workflow_id = input.workflow_id
        request_id = input.request_id

        log.info(
            "hatchet_run_started",
            event_domain="audit_run",
            run_id=run_id,
            workflow_id=workflow_id,
            request_id=request_id,
            worker_id=ctx.worker_id,
            pool=input.extract_pool,
            timeout_minutes=settings.hatchet_task_timeout_minutes,
        )
        try:
            from audit_workbench.db.base import async_session_factory
            from audit_workbench.db.models import Run
            from audit_workbench.observability.context import log_context
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
                    hatchet_worker_id=ctx.worker_id,
                ):
                    async with async_session_factory() as session:
                        if workflow_id is None:
                            run = await session.get(Run, run_id)
                            workflow_id = run.workflow_id if run else None
                            if workflow_id:
                                from audit_workbench.observability.context import bind_log_context

                                bind_log_context(workflow_id=workflow_id)
                        await execute_run_with_timeout(session, run_id)
        except Exception as exc:
            from audit_workbench.services.run_terminal import (
                PUBLIC_RUN_FAILURE_MESSAGE,
                fail_run_terminal,
            )

            if isinstance(exc, TimeoutError):
                log.warning(
                    "hatchet_run_timed_out",
                    run_id=run_id,
                    timeout_minutes=settings.hatchet_task_timeout_minutes,
                )
            else:
                log.exception("hatchet_run_failed", run_id=run_id, error=repr(exc))
            await fail_run_terminal(run_id, PUBLIC_RUN_FAILURE_MESSAGE)
            raise
        log.info("hatchet_run_completed", run_id=run_id, pool=input.extract_pool)
        return {"run_id": run_id, "phase": "done"}

    return workflow


def get_audit_run_workflow():
    global _audit_run_workflow
    if _audit_run_workflow is None:
        from audit_workbench.hatchet.client import get_hatchet

        _audit_run_workflow = register_audit_run_workflow(get_hatchet())
    return _audit_run_workflow


def worker_pool_labels(pool: str) -> list[DesiredWorkerLabel]:
    return [DesiredWorkerLabel(key="pool", value=pool, required=True)]
