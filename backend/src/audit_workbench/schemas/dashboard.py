from audit_workbench.schemas.audit import AuditListItem
from audit_workbench.schemas.common import CamelModel
from audit_workbench.schemas.metrics import MetricsResponse
from audit_workbench.schemas.workflow import WorkflowSchema


class QueueSnapshot(CamelModel):
    queued_runs: int
    running_runs: int
    inflight_runs: int


class DashboardResponse(CamelModel):
    metrics: MetricsResponse
    audits: list[AuditListItem]
    workflows: list[WorkflowSchema]
    queue: QueueSnapshot
