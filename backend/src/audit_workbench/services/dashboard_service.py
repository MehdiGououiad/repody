from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.base import async_session_factory
from audit_workbench.schemas.dashboard import DashboardResponse, QueueSnapshot
from audit_workbench.services import metrics_service
from audit_workbench.services.admission import queue_snapshot_counts
from audit_workbench.services.audit.query import list_completed_audits
from audit_workbench.services.workflow.service import list_workflows

_DASHBOARD_AUDIT_LIMIT = 50


async def get_dashboard(session: AsyncSession) -> DashboardResponse:
    """Assemble dashboard with parallel short-lived sessions (no shared-session races)."""

    async def _metrics():
        async with async_session_factory() as s:
            return await metrics_service.get_metrics(s)

    async def _audits():
        async with async_session_factory() as s:
            return await list_completed_audits(s, limit=_DASHBOARD_AUDIT_LIMIT)

    async def _workflows():
        async with async_session_factory() as s:
            return await list_workflows(s)

    metrics, audits, workflows, (queued, running, inflight) = await asyncio.gather(
        _metrics(),
        _audits(),
        _workflows(),
        queue_snapshot_counts(session),
    )
    return DashboardResponse(
        metrics=metrics,
        audits=audits,
        workflows=workflows,
        queue=QueueSnapshot(
            queued_runs=queued,
            running_runs=running,
            inflight_runs=inflight,
        ),
    )
