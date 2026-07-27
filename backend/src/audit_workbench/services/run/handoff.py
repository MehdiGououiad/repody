"""Durable handoff to the next agent stage via dispatch outbox reuse."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.models import Run, RunDispatchOutbox
from audit_workbench.platform.contracts.agent import AgentId
from audit_workbench.platform.pools import pool_for_agent
from audit_workbench.services.dispatch_outbox import schedule_outbox_dispatch

log = structlog.get_logger()

_STATUS_PENDING = "pending"


async def schedule_next_agent_stage(
    session: AsyncSession,
    run: Run,
    next_agent: AgentId,
    *,
    request_id: str | None = None,
) -> None:
    """Reuse the outbox row for the next pool/stage and schedule Taskiq dispatch.

    Updates ``worker_pool`` after IDP→fraud/CU handoff, and refreshes
    ``last_activity_at`` so stale reap does not kill mid-pipeline runs.
    """
    idp_pool = (run.worker_pool or "extract").strip().lower()
    # Preserve IDP capacity class when leaving extract/fast for a later agent pool.
    if idp_pool not in {"extract", "fast"}:
        idp_pool = "extract"
    pool = pool_for_agent(next_agent, idp_pool=idp_pool)
    now = datetime.now(UTC)
    run.worker_pool = pool
    run.last_activity_at = now
    row = await session.get(RunDispatchOutbox, run.id)
    if row is None:
        session.add(
            RunDispatchOutbox(
                run_id=run.id,
                pool=pool,
                agent_stage=next_agent.value,
                workflow_id=run.workflow_id,
                request_id=request_id,
                status=_STATUS_PENDING,
                dispatch_attempts=0,
            )
        )
    else:
        row.pool = pool
        row.agent_stage = next_agent.value
        row.workflow_id = run.workflow_id
        if request_id is not None:
            row.request_id = request_id
        row.status = _STATUS_PENDING
        row.dispatch_attempts = 0
        row.dispatched_at = None
        row.error = None
    await session.commit()
    schedule_outbox_dispatch(run.id)
    log.info(
        "agent_stage_handoff_scheduled",
        event_domain="audit_run",
        run_id=run.id,
        next_agent=next_agent.value,
        pool=pool,
    )
