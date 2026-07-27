"""IDP frozen contracts — workflow, documents, extraction, validation, outcomes."""

from __future__ import annotations

from dataclasses import dataclass

from audit_workbench.extraction.types import ExtractionMetadata
from audit_workbench.platform.contracts.result import AppError


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
class DocumentExtraction:
    document_id: str
    fields: tuple[ExtractedField, ...]
    markdown_text: str | None
    meta: ExtractionMetadata
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
    """Handoff artifact for Fraud and Computer Use agents."""

    run_id: str
    workflow_id: str
    extraction: ExtractionOutput
    validation: ValidationOutput
    errors: tuple[AppError, ...] = ()
