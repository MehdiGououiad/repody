"""Health, platform configuration and the dashboard."""

from datetime import date, datetime
from typing import Literal, get_args

from pydantic import Field

from repody.schemas.common import CamelModel
from repody.schemas.credits import Credits
from repody.schemas.rule import Severity
from repody.schemas.run import AuditListItem, RunProgress, RunStatus, Source
from repody.schemas.workflow import WorkflowOut

Permission = Literal[
    "workflow:read",
    "workflow:write",
    "workflow:deploy",
    "workflow:delete",
    "run:read",
    "run:execute",
    "metrics:read",
    "credits:grant",
]
PERMISSIONS: tuple[Permission, ...] = get_args(Permission)


class Access(CamelModel):
    """What the caller may do: the web app shows or disables each action from it."""

    roles: list[str]
    permissions: list[Permission]
    with_credits: list[Permission] = Field(
        default_factory=list,
        description="A playground visitor's paid actions: offered, answered 402 (contact us).",
    )
    credits: Credits | None = Field(default=None, description="None when signed out.")


class Health(CamelModel):
    status: Literal["ok", "degraded"]
    database: bool = True
    oidc_enabled: bool = Field(description="Whether API calls need a Keycloak token.")


class PlatformConfig(CamelModel):
    served_model: str
    llamacpp_base_url: str
    model_available: bool | None  # None: not probed (an endpoint that scales to zero)
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
    passed: int
    warning: int
    failed: int


class DurationStats(CamelModel):
    """Finished runs of the last 7 days, from start to finish."""

    median_ms: int
    p95_ms: int
    extraction_median_ms: int


class SourceCounts(CamelModel):
    """Runs of the last 7 days by who started them."""

    api: int
    test: int


class HourRuns(CamelModel):
    day: date = Field(description="UTC day.")
    hour: int = Field(ge=0, le=23, description="UTC hour; clients shift it to their time zone.")
    runs: int


class DocumentTypeCount(CamelModel):
    document_type: str
    documents: int
    pages: int


class DocumentStats(CamelModel):
    """Documents read in the last 7 days, and their pages."""

    documents: int
    pages: int
    by_type: list[DocumentTypeCount]


class WorkflowActivity(CamelModel):
    workflow_id: str
    runs: list[int] = Field(description="Runs per UTC day, the last 7 days, oldest first.")
    median_ms: int


class SeverityShare(CamelModel):
    severity: Severity
    share: float


class QueueCounts(CamelModel):
    queued_runs: int
    running_runs: int


class Dashboard(CamelModel):
    kpis: list[Kpi]
    performance_series: list[DayRuns] = Field(description="The last 14 UTC days, oldest first.")
    timing: DurationStats
    sources: SourceCounts
    hourly: list[HourRuns] = Field(
        description="Runs per UTC hour, the last 7 days (hours with runs)."
    )
    documents: DocumentStats
    workflow_activity: list[WorkflowActivity]
    failures_by_severity: list[SeverityShare]
    queue: QueueCounts
    recent_audits: list[AuditListItem]
    failed_audits: list[AuditListItem]
    workflows: list[WorkflowOut] = Field(description="The most recently edited workflows.")


class ActiveRun(CamelModel):
    id: str
    workflow_id: str
    workflow_name: str
    status: RunStatus
    source: Source
    files: list[str]
    created_at: datetime
    started_at: datetime | None
    progress: RunProgress | None


class FailedRun(CamelModel):
    id: str
    workflow_id: str
    workflow_name: str
    source: Source
    error: str
    created_at: datetime


class HourThroughput(CamelModel):
    hour: datetime = Field(description="The start of the UTC hour.")
    done: int
    failed: int


class Operations(CamelModel):
    """The control room: what runs now, what broke, how fast the platform works."""

    queue: QueueCounts
    active: list[ActiveRun]
    errors: list[FailedRun] = Field(
        description="Runs that failed (not judged) in the last 24 hours."
    )
    throughput: list[HourThroughput] = Field(description="The last 24 UTC hours, oldest first.")
    timing: DurationStats
