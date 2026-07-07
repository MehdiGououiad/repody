from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.schemas.dashboard import DashboardResponse, QueueSnapshot
from audit_workbench.services.admission import count_inflight, count_queued, count_running
from audit_workbench.services.audit.query import list_completed_audits
from audit_workbench.services import metrics_service
from audit_workbench.services.workflow.service import list_workflows

_DASHBOARD_AUDIT_LIMIT = 50


async def get_dashboard(session: AsyncSession) -> DashboardResponse:
    metrics = await metrics_service.get_metrics(session)
    audits = await list_completed_audits(session, limit=_DASHBOARD_AUDIT_LIMIT)
    workflows = await list_workflows(session)
    queued_runs = await count_queued(session)
    running_runs = await count_running(session)
    inflight_runs = await count_inflight(session)
    return DashboardResponse(
        metrics=metrics,
        audits=audits,
        workflows=workflows,
        queue=QueueSnapshot(
            queued_runs=queued_runs,
            running_runs=running_runs,
            inflight_runs=inflight_runs,
        ),
    )
