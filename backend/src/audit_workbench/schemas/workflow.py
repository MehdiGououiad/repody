from pydantic import Field

from audit_workbench.schemas.common import CamelModel
from audit_workbench.schemas.run import RunAuditDetail, RunAuditField, RunAuditRule


class SchemaFieldSchema(CamelModel):
    id: str
    name: str
    description: str = ""
    template_type: str = Field(
        default="verbatim-string",
        serialization_alias="templateType",
    )


class DocumentDefSchema(CamelModel):
    id: str
    document_type: str = ""
    extraction_mode: str = Field(
        default="document_model",
        serialization_alias="extractionMode",
        description="Read path id from GET /processing-paths (document_model).",
    )
    validation_mode: str = Field(
        default="logic_only",
        serialization_alias="validationMode",
        description="logic_only",
    )
    ocr_model: str | None = Field(
        default="repody:vlm",
        serialization_alias="ocrModel",
    )
    schema_fields: list[SchemaFieldSchema] = Field(
        default_factory=list,
        validation_alias="schema",
        serialization_alias="schema",
    )
    extraction_instructions: str = Field(
        default="",
        serialization_alias="extractionInstructions",
    )
    markdown_extraction: bool = Field(
        default=False,
        serialization_alias="markdownExtraction",
        description="Run NuExtract document-to-Markdown in parallel with field extraction.",
    )


class WorkflowRuleSchema(CamelModel):
    id: str
    name: str
    kind: str = "logic"
    scope: str = "intra"
    applies_to: list[str] = []
    conditions: list[dict] | None = None
    condition_junction: str | None = None
    body: str = ""
    severity: str = "reject"


class TopFailingRuleSchema(CamelModel):
    name: str
    count: int
    severity: str


class CallSeriesPointSchema(CamelModel):
    day: str
    calls: int


class WorkflowApiStatsSchema(CamelModel):
    api_calls_today: int
    api_calls_total: int
    avg_latency_ms: int
    call_series: list[CallSeriesPointSchema]
    top_failing_rules: list[TopFailingRuleSchema]


class WorkflowSchema(CamelModel):
    id: str
    name: str
    description: str = ""
    status: str = "draft"
    owner: str = "Me"
    last_run: str | None = None
    success_rate: float = 0.0
    total_runs: int = 0
    documents: list[DocumentDefSchema] = []
    rules: list[WorkflowRuleSchema] = []
    deployed_at: str | None = None
    api_key: str | None = Field(
        default=None,
        description="Plaintext key — returned only once on deploy.",
    )
    api_key_hint: str | None = Field(
        default=None,
        serialization_alias="apiKeyHint",
        description="Masked hint for deployed workflows.",
    )
    default_llm_model: str | None = Field(default=None, serialization_alias="defaultLlmModel")
    api_stats: WorkflowApiStatsSchema | None = None


class WorkflowListResponse(CamelModel):
    workflows: list[WorkflowSchema]


class WorkflowResponse(CamelModel):
    workflow: WorkflowSchema


class CreateWorkflowBody(CamelModel):
    name: str = "Untitled workflow"
    description: str = ""
    owner: str = "Me"


class BulkDeleteWorkflowsBody(CamelModel):
    ids: list[str] = Field(min_length=1)


class DeployWorkflowBody(CamelModel):
    api_key: str | None = None


class DryRunFieldInput(CamelModel):
    id: str
    name: str
    description: str = ""
    template_type: str = Field(default="verbatim-string", serialization_alias="templateType")
    sample_value: str | None = Field(default=None, serialization_alias="sampleValue")


class DryRunRuleInput(CamelModel):
    id: str
    name: str
    kind: str
    body: str = ""
    severity: str = "reject"
    conditions: list[dict] | None = None
    condition_junction: str | None = None


class DryRunBody(CamelModel):
    fields: list[DryRunFieldInput] = []
    rules: list[DryRunRuleInput] = []
    documents: list[DocumentDefSchema] | None = None
    rules_full: list[WorkflowRuleSchema] | None = None


class DryRunExtracted(CamelModel):
    field: str
    value: str
    matched: bool


class DryRunRuleResult(CamelModel):
    id: str
    name: str
    kind: str
    status: str
    detail: str


class DryRunResponse(CamelModel):
    extracted: list[DryRunExtracted]
    rule_results: list[DryRunRuleResult] = Field(serialization_alias="ruleResults")


class RunCreatedResponse(CamelModel):
    run_id: str = Field(serialization_alias="runId")
    job_id: str | None = Field(default=None, serialization_alias="jobId")
    status: str = "queued"


class RunProgressStepSchema(CamelModel):
    id: str
    label: str
    status: str
    mode: str | None = None
    kind: str | None = None
    detail: str | None = None
    read_path: str | None = Field(default=None, serialization_alias="readPath")
    validation_mode: str | None = Field(default=None, serialization_alias="validationMode")
    ocr_model: str | None = Field(default=None, serialization_alias="ocrModel")
    duration_ms: int | None = Field(default=None, serialization_alias="durationMs")
    gpu_cold_start_hint: bool = Field(default=False, serialization_alias="gpuColdStartHint")


class RunProgressSchema(CamelModel):
    current_index: int = Field(serialization_alias="currentIndex")
    steps: list[RunProgressStepSchema]
    label: str
    queue_position: int | None = Field(default=None, serialization_alias="queuePosition")
    queue_depth: int | None = Field(default=None, serialization_alias="queueDepth")


class RunPollResponse(CamelModel):
    status: str
    progress: RunProgressSchema | None = None
    result: RunAuditDetail | None = None
    error: str | None = None


class RuleTemplateSchema(CamelModel):
    id: str
    name: str
    kind: str
    scope: str
    description: str
    body: str
    severity: str


class RuleLibraryResponse(CamelModel):
    templates: list[RuleTemplateSchema]


# Re-export run schemas for OpenAPI
__all__ = [
    "RunAuditDetail",
    "RunAuditField",
    "RunAuditRule",
]
