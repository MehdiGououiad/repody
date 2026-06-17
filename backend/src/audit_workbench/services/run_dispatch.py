"""Dispatch audit runs to Hatchet workers."""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.models import RunStatus
from audit_workbench.hatchet.workflows.audit_run import (
    AuditRunInput,
    get_audit_run_workflow,
    worker_pool_labels,
)
from audit_workbench.services.run_pool_classifier import resolve_worker_pool
from audit_workbench.services.run_terminal import (
    PUBLIC_DISPATCH_FAILURE_MESSAGE,
    fail_run_terminal,
)
from audit_workbench.settings import get_settings

log = structlog.get_logger()


async def mark_run_dispatch_failed(run_id: str, exc: Exception) -> None:
    """Mark a queued run failed when Hatchet dispatch fails after the API commit."""
    await fail_run_terminal(
        run_id,
        PUBLIC_DISPATCH_FAILURE_MESSAGE,
        expected_status=RunStatus.queued.value,
    )
    log.warning(
        "hatchet_dispatch_failed_terminal",
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
    """Trigger the audit-run Hatchet workflow after the API transaction commits."""
    settings = get_settings()
    if pool is None:
        if session is None:
            from audit_workbench.db.base import async_session_factory

            async with async_session_factory() as owned:
                pool = await resolve_worker_pool(owned, run_id)
        else:
            pool = await resolve_worker_pool(session, run_id)

    workflow = get_audit_run_workflow()
    ref = await workflow.aio_run_no_wait(
        AuditRunInput(
            run_id=run_id,
            extract_pool=pool,
            workflow_id=workflow_id,
            request_id=request_id,
        ),
        child_key=run_id,
        additional_metadata={
            "run_id": run_id,
            "pool": pool,
            "workflow_id": workflow_id,
            "request_id": request_id,
        },
        desired_worker_labels=worker_pool_labels(pool),
    )
    workflow_run_id = getattr(ref, "workflow_run_id", None) or getattr(ref, "run_id", run_id)
    log.info(
        "hatchet_run_dispatched",
        event_domain="audit_run",
        run_id=run_id,
        workflow_id=workflow_id,
        request_id=request_id,
        pool=pool,
        workflow_run_id=workflow_run_id,
        host=settings.hatchet_client_host_port,
    )
    return run_id


async def close_hatchet_client() -> None:
    from audit_workbench.hatchet.client import clear_hatchet_client

    clear_hatchet_client()
