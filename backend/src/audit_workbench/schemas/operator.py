"""Operator panel API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from audit_workbench.schemas.common import CamelModel


class OperatorWarmupConfig(CamelModel):
    document_model_on_start: bool = Field(serialization_alias="documentModelOnStart")


class OperatorLimitsSchema(CamelModel):
    max_upload_bytes: int = Field(serialization_alias="maxUploadBytes")
    ocr_max_pages: int = Field(serialization_alias="ocrMaxPages")
    task_timeout_minutes: int = Field(serialization_alias="taskTimeoutMinutes")


class OperatorStatusResponse(CamelModel):
    actions_enabled: bool = Field(serialization_alias="actionsEnabled")
    report_directory: str = Field(serialization_alias="reportDirectory")
    warmup: OperatorWarmupConfig
    limits: OperatorLimitsSchema


class OperatorJobSchema(CamelModel):
    id: str
    kind: str
    label: str
    status: str
    created_at: datetime = Field(serialization_alias="createdAt")
    started_at: datetime | None = Field(default=None, serialization_alias="startedAt")
    completed_at: datetime | None = Field(default=None, serialization_alias="completedAt")
    progress: str = ""
    output: str = ""
    error: str | None = None
    has_report: bool = Field(default=False, serialization_alias="hasReport")


class OperatorJobsResponse(CamelModel):
    jobs: list[OperatorJobSchema]


class OperatorJobAcceptedResponse(CamelModel):
    job: OperatorJobSchema


class BenchmarkSummarySchema(CamelModel):
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    field_accuracy: float = Field(default=0.0, serialization_alias="fieldAccuracy")
    rule_accuracy: float = Field(default=0.0, serialization_alias="ruleAccuracy")
    median_wall_ms: float | None = Field(default=None, serialization_alias="medianWallMs")
    ocr_compare_runs: int | None = Field(default=None, serialization_alias="ocrCompareRuns")
    median_raw_text_chars: float | None = Field(
        default=None, serialization_alias="medianRawTextChars"
    )


class BenchmarkResultSchema(CamelModel):
    case: str = ""
    model: str = ""
    phase: str = ""
    status: str = ""
    passed: bool = False
    skipped: bool | None = None
    wall_ms: float | None = Field(default=None, serialization_alias="wallMs")
    queue_ms: float | None = Field(default=None, serialization_alias="queueMs")
    extraction_ms: float | None = Field(default=None, serialization_alias="extractionMs")
    validation_ms: float | None = Field(default=None, serialization_alias="validationMs")
    field_accuracy: float | None = Field(default=None, serialization_alias="fieldAccuracy")
    rule_accuracy: float | None = Field(default=None, serialization_alias="ruleAccuracy")
    ocr_compare: bool | None = Field(default=None, serialization_alias="ocrCompare")
    judge_quality: bool | None = Field(default=None, serialization_alias="judgeQuality")
    raw_text_chars: int | None = Field(default=None, serialization_alias="rawTextChars")
    ocr_text_chars: int | None = Field(default=None, serialization_alias="ocrTextChars")
    text_preview: str | None = Field(default=None, serialization_alias="textPreview")
    cache_hit: bool | None = Field(default=None, serialization_alias="cacheHit")
    error: str | None = None


class BenchmarkReportSchema(CamelModel):
    generated_at: str = Field(default="", serialization_alias="generatedAt")
    profile: str = ""
    suite_id: str = Field(default="", serialization_alias="suiteId")
    summary: BenchmarkSummarySchema = Field(default_factory=BenchmarkSummarySchema)
    results: list[BenchmarkResultSchema] = Field(default_factory=list)
    environment: dict[str, Any] = Field(default_factory=dict)
