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

# A definition goes into every model request: bounded so one workflow cannot fill the model's
# context (or the API's memory) on every page it reads.
MAX_DOCUMENTS = 20
MAX_RULES = 200
MAX_FIELDS = 300  # per document, at every level together
MAX_DEPTH = 5  # objects within objects
MAX_CHOICES = 100
MAX_EXAMPLES = 5
MAX_EXAMPLE_CHARS = 20_000


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
    enum_values: list[Name] = Field(default_factory=list, max_length=MAX_CHOICES)
    children: list[SchemaField] = Field(default_factory=list, max_length=MAX_FIELDS)

    @model_validator(mode="after")
    def _choices(self) -> Self:
        if self.template_type in ("enum", "multi-enum") and len(self.enum_values) < 2:
            raise ValueError(f"{self.template_type} field {self.name!r} needs at least 2 choices.")
        return self


class IclExample(CamelModel):
    """A NuExtract in-context example: input text and the JSON it should produce."""

    input: Annotated[str, StringConstraints(max_length=MAX_EXAMPLE_CHARS)]
    output: Annotated[str, StringConstraints(max_length=MAX_EXAMPLE_CHARS)]


class DocumentDef(CamelModel):
    id: Id
    document_type: Name = ""
    schema_fields: list[SchemaField] = Field(
        default_factory=list, alias="schema", max_length=MAX_FIELDS
    )
    extraction_instructions: Text = ""
    markdown_extraction: bool = Field(
        default=False, description="Transcribe the document to Markdown when it has no fields."
    )
    extraction_icl_examples: list[IclExample] = Field(default_factory=list, max_length=MAX_EXAMPLES)

    @model_validator(mode="after")
    def _bounded(self) -> Self:
        def walk(fields: list[SchemaField], depth: int) -> int:
            if fields and depth > MAX_DEPTH:
                raise ValueError(f"Fields nest at most {MAX_DEPTH} levels deep.")
            return sum(1 + walk(f.children, depth + 1) for f in fields)

        if walk(self.schema_fields, 1) > MAX_FIELDS:
            raise ValueError(f"A document has at most {MAX_FIELDS} fields.")
        return self

    @property
    def wants_extraction(self) -> bool:
        return bool(self.schema_fields) or self.markdown_extraction


class WorkflowDefinition(CamelModel):
    """What a run executes; stored as JSON on the workflow and copied onto each run."""

    documents: list[DocumentDef] = Field(default_factory=list, max_length=MAX_DOCUMENTS)
    rules: list[Rule] = Field(default_factory=list, max_length=MAX_RULES)

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
    read_only: bool = Field(
        default=False, description="Shared (no account): duplicate it to edit or run it."
    )


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
