"""A workflow: documents to extract (NuExtract schema) and rules to check."""

from collections import Counter
from datetime import date, datetime
from typing import Annotated, Literal, Self

from pydantic import Field, StringConstraints, model_validator

from repody.schemas.catalog import DEFAULT_TYPE, TemplateType, field_key
from repody.schemas.common import CamelModel, Id, Name, Text
from repody.schemas.rule import Rule, Severity

# The workflow lifecycle (repody.app.lifecycle). Archived workflows are never returned, so the
# API's status is draft or active; deploying makes a workflow active.
WorkflowState = Literal["draft", "active", "archived"]
WorkflowStatus = Literal["draft", "active"]


class SchemaField(CamelModel):
    """One NuExtract template field.

    ``template_type`` is a NuExtract leaf type (``verbatim-string``, ``number``, …),
    ``<leaf>-list``, ``enum`` / ``multi-enum`` (with ``enum_values``) or ``object`` /
    ``object-array`` (with ``children``).
    """

    id: Id = ""
    name: Name
    description: Text = ""
    template_type: TemplateType = DEFAULT_TYPE
    enum_values: list[Name] = Field(default_factory=list)
    children: list[SchemaField] = Field(default_factory=list)

    @model_validator(mode="after")
    def _choices(self) -> Self:
        if self.template_type in ("enum", "multi-enum") and len(self.enum_values) < 2:
            raise ValueError(f"{self.template_type} field {self.name!r} needs at least 2 choices.")
        return self


class IclExample(CamelModel):
    """A NuExtract in-context example: input text and the JSON it should produce."""

    input: Annotated[str, StringConstraints(max_length=100_000)]
    output: Annotated[str, StringConstraints(max_length=100_000)]


class DocumentDef(CamelModel):
    id: Id
    document_type: Name = ""
    schema_fields: list[SchemaField] = Field(default_factory=list, alias="schema")
    extraction_instructions: Text = ""
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
    def _unique_field_names(self) -> Self:
        """Names are unique at every level, compared as rules read them (``field_key``:
        ``Unit Price`` and ``unit_price`` are the same field)."""

        def check(fields: list[SchemaField], where: str) -> None:
            counts = Counter(field_key(f.name) for f in fields if f.name)
            if dupes := sorted(key for key, n in counts.items() if n > 1):
                raise ValueError(f"{where}: duplicate field name(s) {', '.join(dupes)}.")
            for f in fields:
                check(f.children, f"{where}.{f.name}")

        for doc in self.documents:
            check(doc.schema_fields, doc.document_type or "Document")
        return self


class CallsPerDay(CamelModel):
    day: date = Field(description="UTC day; clients name it in their locale.")
    calls: int


class FailingRule(CamelModel):
    name: str
    count: int
    severity: Severity


class ApiStats(CamelModel):
    """Runs started with the workflow's API key."""

    api_calls_today: int
    api_calls_total: int
    avg_latency_ms: int
    call_series: list[CallsPerDay]
    top_failing_rules: list[FailingRule]


class CreateWorkflow(CamelModel):
    name: Name = "Untitled workflow"
    description: Text = ""
    owner: Name = ""


class WorkflowIn(CreateWorkflow, WorkflowDefinition):
    """What the builder saves. The status is not part of it: only deploying changes it."""


class WorkflowOut(WorkflowIn):
    id: str
    status: WorkflowStatus = Field(description="active once deployed (it has an API key).")
    deployed_at: datetime | None = None
    api_key: str | None = Field(default=None, description="Plaintext key, returned once on deploy.")
    api_key_hint: str | None = None
    total_runs: int = 0
    success_rate: float = 0.0
    last_run: datetime | None = None
    api_stats: ApiStats | None = None


class WorkflowList(CamelModel):
    workflows: list[WorkflowOut]


class BulkDelete(CamelModel):
    ids: list[Id] = Field(min_length=1, max_length=500)


class RuleCheck(CamelModel):
    rule_id: str
    issues: list[str]
    checks: list[str] = Field(description="Readable form of each condition, in order.")


class RuleChecks(CamelModel):
    rules: list[RuleCheck]
