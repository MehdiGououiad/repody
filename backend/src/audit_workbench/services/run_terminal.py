"""Terminal failure handling for runs (status + progress)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db import base as db_base
from audit_workbench.services.run.adapters.composition import get_fail_run, run_lifecycle_store
from audit_workbench.services.run.application.use_cases import FailRunRequest
from audit_workbench.services.run.domain.entity import DomainRunStatus

PUBLIC_RUN_FAILURE_MESSAGE = (
    "Run failed while processing. Contact an operator with the run id for details."
)
PUBLIC_DISPATCH_FAILURE_MESSAGE = (
    "Run dispatch failed. Retry the run or contact an operator."
)


async def fail_run_terminal(
    run_id: str,
    error: str,
    *,
    session: AsyncSession | None = None,
    expected_status: str | None = None,
) -> bool:
    """Mark a run failed and publish a terminal progress snapshot for SSE subscribers."""
    domain_expected = DomainRunStatus(expected_status) if expected_status is not None else None
    request = FailRunRequest(
        run_id=run_id,
        error=error,
        expected_status=domain_expected,
    )
    fail_run = get_fail_run()
    if session is not None:
        return await fail_run.execute(request, store=run_lifecycle_store(session))

    async with db_base.async_session_factory() as owned_session:
        return await fail_run.execute(request, store=run_lifecycle_store(owned_session))
