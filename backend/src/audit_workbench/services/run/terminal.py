"""Terminal failure handling for runs (status + progress)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db import base as db_base
from audit_workbench.services.run.events import publish_run_domain_events
from audit_workbench.services.run.persistence import (
    bind_commit,
    bind_load,
    bind_save,
)
from audit_workbench.services.run.commands import FailRunRequest, fail_run
from audit_workbench.services.run.lifecycle import RunStatus

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
    domain_expected = RunStatus(expected_status) if expected_status is not None else None
    request = FailRunRequest(
        run_id=run_id,
        error=error,
        expected_status=domain_expected,
    )

    async def _execute(owned: AsyncSession) -> bool:
        return await fail_run(
            request,
            load=bind_load(owned),
            save=bind_save(owned),
            commit=bind_commit(owned),
            publish=publish_run_domain_events,
        )

    if session is not None:
        return await _execute(session)

    async with db_base.async_session_factory() as owned_session:
        return await _execute(owned_session)
