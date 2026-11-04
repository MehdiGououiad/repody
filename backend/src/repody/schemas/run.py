"""Runs: live progress while queued or running, and the audit report once done."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, computed_field

from repody.schemas.common import CamelModel

RunStatus = Literal["queued", "running", "done", "failed"]
Outcome = Literal["passed", "warning", "failed"]


class ProgressStep(CamelModel):
    id: str
    label: str
    status: Literal["pending", "active", "done"] = "pending"
    detail: str | None = None
    duration_ms: int | None = None
    cache_hit: bool = False


class RunProgress(CamelModel):
    label: str
    steps: list[ProgressStep] = Field(default_factory=list)
    queue_position: int | None = Field(default=None, description="1-based, while queued.")
    queue_depth: int | None = None


class ExtractionMeta(CamelModel):
    extraction_ms: int = 0
    cache_hit: bool = False
    fields_extracted: int = 0
    pages_rendered: int = 0
    pages_sent: int = 0
    raw_text: str | None = Field(default=None, description="The model's JSON answer.")
    markdown_text: str | None = None


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
    scope: str
    severity: str
    status: Literal["passed", "failed", "skipped"]
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
    source: str
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
    timestamp: datetime
    rows: int
    failed_rules: int


class AuditList(CamelModel):
    audits: list[AuditListItem]
    total: int
    limit: int
    offset: int
