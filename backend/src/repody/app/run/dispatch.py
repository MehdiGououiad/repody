"""Send queued runs to Taskiq workers.

The API commits the run, then sends the task and stamps ``runs.dispatched_at``. If the send
fails (Redis down), the run stays queued with ``dispatched_at`` NULL and maintenance re-sends
it. Delivery after a successful send is Taskiq's job (RedisStreamBroker acks + redelivery);
duplicates are harmless because the worker claim is a conditional UPDATE.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from repody.infra.db import base as db_base
from repody.infra.db.models import Run, RunStatus
from repody.taskiq.broker import shutdown_taskiq_brokers, startup_taskiq_brokers
from repody.taskiq.models import AuditRunInput
from repody.taskiq.tasks import get_process_audit_run_task

log = structlog.get_logger(__name__)

# Leave fresh runs to the API's own send before maintenance re-sends them.
_REDISPATCH_GRACE = timedelta(seconds=30)


async def dispatch_audit_run(
    run_id: str,
    *,
    pool: str,
    workflow_id: str | None = None,
    request_id: str | None = None,
) -> bool:
    """Send the run's task; True once Taskiq accepted it. Never raises."""
    try:
        await startup_taskiq_brokers()
        await get_process_audit_run_task(pool).kiq(
            AuditRunInput(
                run_id=run_id, extract_pool=pool, workflow_id=workflow_id, request_id=request_id
            )
        )
    except Exception as exc:
        log.warning(
            "taskiq_dispatch_failed",
            event_domain="audit_run",
            run_id=run_id,
            pool=pool,
            error=repr(exc),
        )
        return False
    async with db_base.async_session_factory() as session:
        await session.execute(
            update(Run).where(Run.id == run_id).values(dispatched_at=datetime.now(UTC))
        )
        await session.commit()
    log.info(
        "taskiq_run_dispatched",
        event_domain="audit_run",
        run_id=run_id,
        workflow_id=workflow_id,
        request_id=request_id,
        pool=pool,
    )
    return True


async def redispatch_undispatched(session: AsyncSession, *, limit: int = 100) -> int:
    """Re-send queued runs the API never managed to hand to Taskiq."""
    cutoff = datetime.now(UTC) - _REDISPATCH_GRACE
    pending = await session.execute(
        select(Run.id, Run.worker_pool, Run.workflow_id)
        .where(
            Run.status == RunStatus.queued.value,
            Run.dispatched_at.is_(None),
            Run.created_at < cutoff,
        )
        .order_by(Run.created_at)
        .limit(limit)
    )
    sent = 0
    for run_id, pool, workflow_id in pending.all():
        if await dispatch_audit_run(run_id, pool=pool or "fast", workflow_id=workflow_id):
            sent += 1
    return sent


async def close_taskiq_brokers() -> None:
    await shutdown_taskiq_brokers()
