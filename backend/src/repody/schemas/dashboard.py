from repody.schemas.audit import AuditListItem
from repody.schemas.common import CamelModel
from repody.schemas.metrics import MetricsResponse
from repody.schemas.workflow import WorkflowSchema


class QueueSnapshot(CamelModel):
    queued_runs: int
    running_runs: int
    inflight_runs: int


class DashboardResponse(CamelModel):
    metrics: MetricsResponse
    audits: list[AuditListItem]
    workflows: list[WorkflowSchema]
    queue: QueueSnapshot
