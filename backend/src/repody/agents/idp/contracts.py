"""IDP frozen contracts — workflow, documents, extraction, validation, outcomes."""

from __future__ import annotations

from dataclasses import dataclass

from repody.runtime.contracts.result import AppError


@dataclass(frozen=True, slots=True)
class SchemaField:
    name: str
    description: str = ""
    template_type: str | None = None
    enum_values: tuple[str, ...] = ()
    children: tuple[SchemaField, ...] = ()


@dataclass(frozen=True, slots=True)
class DocumentSpec:
    id: str
    label: str
    schema_fields: tuple[SchemaField, ...]
    extraction_instructions: str = ""
    markdown_extraction: bool = False
    native_pdf_auto: bool = False
    document_model_id: str = "repody:vlm"
    extraction_mode: str = "document_model"
    position: int = 0


@dataclass(frozen=True, slots=True)
class RuleSpec:
    id: str
    name: str
    kind: str
    scope: str
    severity: str
    applies_to: tuple[str, ...]
    conditions: tuple[dict, ...] = ()
    body: str = ""
    condition_junction: str | None = None


@dataclass(frozen=True, slots=True)
class IdpWorkflowConfig:
    workflow_id: str
    documents: tuple[DocumentSpec, ...]
    rules: tuple[RuleSpec, ...]
    workflow_name: str | None = None


@dataclass(frozen=True, slots=True)
class StoredDocument:
    document_id: str
    storage_key: str
    mime_type: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class ExtractedField:
    key: str
    value: str
    field_type: str
    extracted: bool
    confidence: float | None = None
    description: str = ""


@dataclass(frozen=True, slots=True)
class IdpExtractionMeta:
    """IDP-owned extraction meta — no display labels (those are HTTP/progress edge)."""

    read_path_config: str
    read_path_used: str
    validation_mode: str
    document_model_id: str | None = None
    extraction_ms: int = 0
    cache_hit: bool = False
    gpu_cold_start_likely: bool = False
    fields_extracted: int = 0
    markdown_extraction: bool = False
    markdown_text: str | None = None
    raw_text: str | None = None
    pages_rendered: int | None = None
    pages_sent: int | None = None
    pages_dropped: int | None = None
    native_pdf: dict | None = None


@dataclass(frozen=True, slots=True)
class DocumentExtraction:
    document_id: str
    fields: tuple[ExtractedField, ...]
    markdown_text: str | None
    meta: IdpExtractionMeta
    raw_text: str | None = None


@dataclass(frozen=True, slots=True)
class ExtractionOutput:
    by_document: tuple[DocumentExtraction, ...]


@dataclass(frozen=True, slots=True)
class RuleResult:
    rule_id: str
    name: str
    status: str
    severity: str
    detail: str
    affected_fields: tuple[str, ...]
    kind: str = "logic"
    scope: str = "intra"
    expression: str = ""
    expected_value: str | None = None
    actual_value: str | None = None


@dataclass(frozen=True, slots=True)
class ValidationOutput:
    rule_results: tuple[RuleResult, ...]
    overall_status: str
    summary_passed: int
    summary_failed: int


@dataclass(frozen=True, slots=True)
class IdpInput:
    run_id: str
    workflow: IdpWorkflowConfig
    documents: tuple[StoredDocument, ...]


@dataclass(frozen=True, slots=True)
class IdpOutcome:
    """Everything one IDP run produced: extraction, validation and soft errors."""

    run_id: str
    workflow_id: str
    extraction: ExtractionOutput
    validation: ValidationOutput
    errors: tuple[AppError, ...] = ()
