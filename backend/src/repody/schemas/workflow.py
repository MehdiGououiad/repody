"""A workflow: documents to extract (NuExtract schema) and rules to check."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from repody.schemas.common import CamelModel
from repody.schemas.rule import Rule

DEFAULT_TEMPLATE_TYPE = "verbatim-string"


class SchemaField(CamelModel):
    """One NuExtract template field.

    ``template_type`` is a NuExtract leaf type (``verbatim-string``, ``number``, …),
    ``<leaf>-list``, ``enum`` / ``multi-enum`` (with ``enum_values``) or ``object`` /
    ``object-array`` (with ``children``).
    """

    id: str = ""
    name: str
    description: str = ""
    template_type: str = DEFAULT_TEMPLATE_TYPE
    enum_values: list[str] = Field(default_factory=list)
    children: list[SchemaField] = Field(default_factory=list)

    @field_validator("name", "description")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()

    @field_validator("template_type")
    @classmethod
    def _default_type(cls, value: str) -> str:
        return value.strip() or DEFAULT_TEMPLATE_TYPE


class IclExample(CamelModel):
    """A NuExtract in-context example: input text and the JSON it should produce."""

    input: str
    output: str


class DocumentDef(CamelModel):
    id: str
    document_type: str = ""
    schema_fields: list[SchemaField] = Field(default_factory=list, alias="schema")
    extraction_instructions: str = ""
    markdown_extraction: bool = Field(
        default=False, description="Transcribe the document to Markdown when it has no fields."
    )
    extraction_icl_examples: list[IclExample] = Field(default_factory=list)

    @property
    def wants_extraction(self) -> bool:
        return bool(self.schema_fields) or self.markdown_extraction


class WorkflowDefinition(CamelModel):
    """What a run executes; stored as JSON on the workflow and copied onto each run."""

    documents: list[DocumentDef] = Field(default_factory=list)
    rules: list[Rule] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_field_names(self) -> WorkflowDefinition:
        for doc in self.documents:
            names = [f.name.lower() for f in doc.schema_fields if f.name]
            dupes = sorted({n for n in names if names.count(n) > 1})
            if dupes:
                raise ValueError(
                    f"{doc.document_type or 'Document'}: duplicate field name(s) {', '.join(dupes)}."
                )
        return self


WorkflowStatus = Literal["draft", "active", "paused"]


class CallsPerDay(CamelModel):
    day: str
    calls: int


class FailingRule(CamelModel):
    name: str
    count: int
    severity: str


class ApiStats(CamelModel):
    """Runs started with the workflow's API key."""

    api_calls_today: int
    api_calls_total: int
    avg_latency_ms: int
    call_series: list[CallsPerDay]
    top_failing_rules: list[FailingRule]


class WorkflowIn(WorkflowDefinition):
    name: str = "Untitled workflow"
    description: str = ""
    status: WorkflowStatus = "draft"
    owner: str = ""


class WorkflowOut(WorkflowIn):
    id: str
    deployed_at: datetime | None = None
    api_key: str | None = Field(default=None, description="Plaintext key, returned once on deploy.")
    api_key_hint: str | None = None
    total_runs: int = 0
    success_rate: float = 0.0
    last_run: datetime | None = None
    api_stats: ApiStats | None = None


class WorkflowList(CamelModel):
    workflows: list[WorkflowOut]


class CreateWorkflow(CamelModel):
    name: str = "Untitled workflow"
    description: str = ""
    owner: str = ""


class BulkDelete(CamelModel):
    ids: list[str] = Field(min_length=1)


class RuleCheck(CamelModel):
    rule_id: str
    issues: list[str]
    checks: list[str] = Field(description="Readable form of each condition, in order.")


class RuleChecks(CamelModel):
    rules: list[RuleCheck]
