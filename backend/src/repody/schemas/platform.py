"""Health, platform configuration and the dashboard."""

from datetime import date
from typing import Literal

from pydantic import Field

from repody.schemas.common import CamelModel
from repody.schemas.rule import Severity
from repody.schemas.run import AuditListItem
from repody.schemas.workflow import WorkflowOut


class Health(CamelModel):
    status: Literal["ok", "degraded"]
    database: bool = True
    redis: bool = True
    oidc_enabled: bool = Field(description="Whether API calls need a Keycloak token.")


class PlatformConfig(CamelModel):
    served_model: str
    llamacpp_base_url: str
    model_available: bool
    cache_enabled: bool
    max_upload_bytes: int
    max_upload_files: int
    max_pages_per_document: int | None
    run_timeout_minutes: int


class KpiPoint(CamelModel):
    day: date
    value: float


KpiId = Literal["auditsWeek", "passRate", "failures"]


class Kpi(CamelModel):
    id: KpiId
    value: float
    previous: float
    series: list[KpiPoint]


class DayRuns(CamelModel):
    day: date = Field(description="UTC day; clients name it in their locale.")
    runs: int
    prev_runs: int


class SeverityShare(CamelModel):
    severity: Severity
    share: float


class QueueCounts(CamelModel):
    queued_runs: int
    running_runs: int


class Dashboard(CamelModel):
    kpis: list[Kpi]
    performance_series: list[DayRuns]
    failures_by_severity: list[SeverityShare]
    stale_runs: int
    queue: QueueCounts
    recent_audits: list[AuditListItem]
    failed_audits: list[AuditListItem]
    workflows: list[WorkflowOut] = Field(description="The most recently edited workflows.")
