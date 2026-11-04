"""Ephemeral per-run workflow config (microservice boundary - no workflow mutation)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from repody.app.run.helpers import rule_dict_from_row, rules_payload
from repody.extraction.types import ExtractionIclExample, SchemaFieldSpec
from repody.infra.db.models import Document, Run, Workflow
from repody.util.json_shape import normalize_keys_to_snake


class SnapshotDocument(BaseModel):
    """A workflow document as one run sees it: from the run snapshot or the live workflow."""

    model_config = ConfigDict(extra="ignore")

    id: str
    document_type: str = ""
    position: int = 0
    extraction_instructions: str = ""
    markdown_extraction: bool = False
    extraction_icl_examples: list[ExtractionIclExample] = Field(default_factory=list)
    schema_fields: list[SchemaFieldSpec] = Field(
        default_factory=list, validation_alias=AliasChoices("schema_fields", "schema")
    )

    @field_validator("extraction_icl_examples", mode="before")
    @classmethod
    def _complete_examples(cls, value: Any) -> list[Any]:
        return [
            ex
            for ex in value or []
            if isinstance(ex, dict) and ex.get("input") and ex.get("output")
        ]

    @field_validator("schema_fields", mode="after")
    @classmethod
    def _named_fields(cls, value: list[SchemaFieldSpec]) -> list[SchemaFieldSpec]:
        return [field for field in value if field.name]


def build_run_snapshot(
    *,
    documents: list[dict] | None = None,
    rules: list[dict] | None = None,
    workflow_name: str | None = None,
) -> dict | None:
    if not documents and not rules and not workflow_name:
        return None
    out: dict = {}
    if documents:
        out["documents"] = [normalize_keys_to_snake(doc) for doc in documents]
    if rules:
        out["rules"] = [normalize_keys_to_snake(rule) for rule in rules]
    if workflow_name:
        out["workflow_name"] = workflow_name
    return out


def _document_from_orm(doc: Document) -> SnapshotDocument:
    return SnapshotDocument.model_validate(
        {
            "id": doc.id,
            "document_type": doc.document_type,
            "position": doc.position,
            "extraction_instructions": doc.extraction_instructions,
            "markdown_extraction": doc.markdown_extraction,
            "extraction_icl_examples": doc.extraction_icl_examples,
            "schema_fields": [
                {
                    "name": f.name,
                    "description": f.description,
                    "template_type": f.template_type,
                    "field_config": f.field_config,
                }
                for f in sorted(doc.schema_fields, key=lambda x: x.position)
            ],
        }
    )


@dataclass(frozen=True, slots=True)
class MaterializedRunConfig:
    """One read of a Run's snapshot (or live Workflow) for the whole execution."""

    documents: list[SnapshotDocument]
    rules: list[dict]
    workflow_name: str


def _documents_from(snapshot: dict, workflow: Workflow | None) -> list[SnapshotDocument]:
    raw_docs = snapshot.get("documents")
    if raw_docs:
        return [
            SnapshotDocument.model_validate(
                {**doc, "id": doc.get("id") or f"doc-{idx}", "position": idx}
            )
            for idx, doc in enumerate(raw_docs)
        ]
    if workflow is None or not getattr(workflow, "documents", None):
        return []
    return [_document_from_orm(doc) for doc in sorted(workflow.documents, key=lambda d: d.position)]


def _rules_from(snapshot: dict, workflow: Workflow | None) -> list[dict]:
    raw_rules = snapshot.get("rules")
    if raw_rules:
        return [
            rule_dict_from_row(
                rule_id=str(rule.get("id") or f"rule-{idx}"),
                name=str(rule.get("name") or "Rule"),
                kind=str(rule.get("kind") or "logic"),
                scope=str(rule.get("scope") or "intra"),
                applies_to=rule.get("applies_to") or [],
                body=str(rule.get("body") or ""),
                severity=str(rule.get("severity") or "reject"),
                conditions=rule.get("conditions"),
                condition_junction=rule.get("condition_junction"),
            )
            for idx, rule in enumerate(raw_rules)
        ]
    if workflow is None:
        return []
    return rules_payload(workflow)


def _workflow_name_from(snapshot: dict, workflow: Workflow | None) -> str:
    return str(snapshot.get("workflow_name") or getattr(workflow, "name", None) or "Workflow")


def materialize_run_config(run: Run) -> MaterializedRunConfig:
    """Normalize the Run snapshot once. Callers must not re-resolve documents or rules."""
    snapshot = normalize_keys_to_snake(run.run_snapshot or {})
    workflow = run.workflow
    return MaterializedRunConfig(
        documents=_documents_from(snapshot, workflow),
        rules=_rules_from(snapshot, workflow),
        workflow_name=_workflow_name_from(snapshot, workflow),
    )


def resolve_workflow_display_name(run: Run, workflow: Workflow) -> str:
    snapshot = normalize_keys_to_snake(run.run_snapshot or {})
    return _workflow_name_from(snapshot, workflow)
