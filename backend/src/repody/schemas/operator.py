"""Operator panel API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from repody.schemas.common import CamelModel


class OperatorWarmupConfig(CamelModel):
    document_model_on_start: bool


class OperatorLimitsSchema(CamelModel):
    max_upload_bytes: int
    nuextract_max_pages_per_request: int | None = None
    task_timeout_minutes: int


class OperatorStatusResponse(CamelModel):
    actions_enabled: bool
    report_directory: str
    warmup: OperatorWarmupConfig
    limits: OperatorLimitsSchema


class OperatorJobSchema(CamelModel):
    id: str
    kind: str
    label: str
    status: str
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    progress: str = ""
    output: str = ""
    error: str | None = None
    has_report: bool = False


class OperatorJobsResponse(CamelModel):
    jobs: list[OperatorJobSchema]


class OperatorJobAcceptedResponse(CamelModel):
    job: OperatorJobSchema


class BenchmarkSummarySchema(CamelModel):
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    field_accuracy: float = 0.0
    rule_accuracy: float = 0.0
    median_wall_ms: float | None = None
    median_raw_text_chars: float | None = None


class BenchmarkResultSchema(CamelModel):
    case: str = ""
    model: str = ""
    phase: str = ""
    status: str = ""
    passed: bool = False
    skipped: bool | None = None
    wall_ms: float | None = None
    queue_ms: float | None = None
    extraction_ms: float | None = None
    validation_ms: float | None = None
    field_accuracy: float | None = None
    rule_accuracy: float | None = None
    judge_quality: bool | None = None
    raw_text_chars: int | None = None
    text_preview: str | None = None
    cache_hit: bool | None = None
    error: str | None = None


class BenchmarkReportSchema(CamelModel):
    generated_at: str = ""
    profile: str = ""
    suite_id: str = ""
    summary: BenchmarkSummarySchema = Field(default_factory=BenchmarkSummarySchema)
    results: list[BenchmarkResultSchema] = Field(default_factory=list)
    environment: dict[str, Any] = Field(default_factory=dict)
