"""Runs: live progress while queued or running, and the audit report once done."""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import Field, computed_field

from repody.schemas.common import CamelModel
from repody.schemas.rule import Scope, Severity

Source = Literal["test", "api"]  # a builder test run, or a run started with the API key
RunStatus = Literal["queued", "running", "done", "failed"]  # lifecycle: repody.app.lifecycle
Outcome = Literal["passed", "warning", "failed"]  # a done run's result
# A filter on outcomes: one outcome, or "review" for every run a person must look at.
OutcomeFilter = Literal["passed", "warning", "failed", "review"]
REVIEW_OUTCOMES: tuple[Outcome, ...] = ("warning", "failed")
RuleStatus = Literal["passed", "failed", "skipped"]


StepKind = Literal["queue", "model", "extract", "rules", "finalize"]


class ProgressStep(CamelModel):
    """One step of a run. Clients word it from its kind and data (no server-side text)."""

    id: str
    kind: StepKind
    status: Literal["pending", "active", "done"] = "pending"
    document_type: str | None = Field(default=None, description="extract steps.")
    rule_count: int | None = Field(default=None, description="rules steps.")
    fields_extracted: int | None = Field(default=None, description="Done extract steps.")
    duration_ms: int | None = None
    failed: bool = Field(default=False, description="Done extract steps whose extraction failed.")
    cold_start: bool = Field(
        default=False,
        description="model step: the model server was asleep (no requests for a while) and is "
        "starting, or started for this run.",
    )


class RunProgress(CamelModel):
    steps: list[ProgressStep] = Field(default_factory=list)


class ExtractionMeta(CamelModel):
    extraction_ms: int = 0
    fields_extracted: int = 0
    pages_rendered: int = 0
    pages_sent: int = 0
    raw_text: str | None = Field(default=None, description="The model's JSON answer.")
    markdown_text: str | None = None
    error: str | None = Field(
        default=None, description="Why extraction failed or its answer was unusable."
    )


class AuditField(CamelModel):
    key: str
    description: str = ""
    type: str = Field(description="NuExtract template type the value follows.")
    value: Any = Field(default=None, description="JSON value; null when not extracted.")
    flagged: bool = False

    @computed_field
    @property
    def extracted(self) -> bool:
        return self.value is not None


class AuditDocument(CamelModel):
    id: str
    document_type: str
    file_name: str
    fields: list[AuditField]
    extraction: ExtractionMeta | None = None


class AuditRule(CamelModel):
    id: str
    rule_id: str
    name: str
    scope: Scope
    severity: Severity
    status: RuleStatus
    expression: str
    detail: str
    affected_fields: list[str]


class RunSummary(CamelModel):
    total: int
    passed: int
    failed: int
    fields_extracted: int


class RunTimings(CamelModel):
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int = 0
    extraction_ms: int = 0
    validation_ms: int = 0


class AuditDetail(CamelModel):
    id: str
    workflow_id: str
    workflow_name: str
    status: Outcome
    source: Source
    created_at: datetime
    documents: list[AuditDocument]
    rule_results: list[AuditRule]
    summary: RunSummary
    metadata: RunTimings


class RunState(CamelModel):
    """What a client polls: status, live progress, and the report once done."""

    status: RunStatus
    progress: RunProgress | None = None
    error: str | None = None
    result: AuditDetail | None = None


class RunCreated(CamelModel):
    run_id: str
    status: RunStatus = "queued"


class AuditListItem(CamelModel):
    id: str
    status: Outcome
    workflow_id: str
    workflow_name: str
    source: Source
    timestamp: datetime
    duration_ms: int
    rows: int
    failed_rules: int
    files: list[str] = Field(description="The uploaded files' names, in workflow order.")
    first_failed_rule: str | None = Field(
        default=None, description="The name of the first failed rule, to say why at a glance."
    )


class AuditList(CamelModel):
    audits: list[AuditListItem]
    total: int
    limit: int
    offset: int


class AuditFilter(CamelModel):
    """Which audits (finished runs) to list or export."""

    q: str = Field(default="", max_length=200, description="Part of the run id or workflow name.")
    outcome: OutcomeFilter | None = Field(
        default=None, description='One outcome, or "review" for warning and failed runs.'
    )
    workflow_id: str | None = None
    day: date | None = Field(default=None, description="Runs created that UTC day.")


class AuditPage(AuditFilter):
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
