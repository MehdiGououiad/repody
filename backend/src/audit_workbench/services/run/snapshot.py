"""Ephemeral per-run workflow config (microservice boundary — no workflow mutation)."""

from __future__ import annotations

from dataclasses import dataclass, field

from audit_workbench.db.models import Document, Run, Workflow
from audit_workbench.extraction.document_modes import normalize_document_modes
from audit_workbench.rules.conditions import resolve_rule_body
from audit_workbench.services.run.helpers import rules_payload


@dataclass
class SnapshotSchemaField:
    id: str
    name: str
    description: str
    position: int
    template_type: str = "verbatim-string"


@dataclass
class SnapshotDocument:
    """Document view for run pipeline — ORM Document or snapshot JSON."""

    id: str
    document_type: str
    position: int
    extraction_mode: str
    validation_mode: str
    ocr_model: str | None
    extraction_instructions: str = ""
    markdown_extraction: bool = False
    schema_fields: list[SnapshotSchemaField] = field(default_factory=list)


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
        out["documents"] = documents
    if rules:
        out["rules"] = rules
    if workflow_name:
        out["workflowName"] = workflow_name
    return out


def _schema_fields_from_snapshot(doc: dict) -> list[SnapshotSchemaField]:
    raw = doc.get("schema") or doc.get("schemaFields") or doc.get("schema_fields") or []
    fields: list[SnapshotSchemaField] = []
    for idx, field_row in enumerate(raw):
        name = (field_row.get("name") or "").strip()
        if not name:
            continue
        fields.append(
            SnapshotSchemaField(
                id=str(field_row.get("id") or f"sf-{idx}"),
                name=name,
                description=str(field_row.get("description") or ""),
                template_type=str(
                    field_row.get("templateType")
                    or field_row.get("template_type")
                    or "verbatim-string"
                ),
                position=idx,
            )
        )
    return fields


def _document_from_snapshot(doc: dict, position: int) -> SnapshotDocument:
    read_id, val_id = normalize_document_modes(
        doc.get("extractionMode") or doc.get("extraction_mode"),
        doc.get("validationMode") or doc.get("validation_mode"),
    )
    return SnapshotDocument(
        id=str(doc.get("id") or f"doc-{position}"),
        document_type=str(doc.get("documentType") or doc.get("document_type") or ""),
        position=position,
        extraction_mode=read_id,
        validation_mode=val_id,
        ocr_model=doc.get("ocrModel") or doc.get("ocr_model"),
        extraction_instructions=str(
            doc.get("extractionInstructions") or doc.get("extraction_instructions") or ""
        ),
        markdown_extraction=bool(
            doc.get("markdownExtraction") or doc.get("markdown_extraction") or False
        ),
        schema_fields=_schema_fields_from_snapshot(doc),
    )


def _document_from_orm(doc: Document) -> SnapshotDocument:
    return SnapshotDocument(
        id=doc.id,
        document_type=doc.document_type,
        position=doc.position,
        extraction_mode=doc.extraction_mode or "auto",
        validation_mode=getattr(doc, "validation_mode", None) or "logic_only",
        ocr_model=doc.ocr_model,
        extraction_instructions=getattr(doc, "extraction_instructions", None) or "",
        markdown_extraction=bool(getattr(doc, "markdown_extraction", False)),
        schema_fields=[
            SnapshotSchemaField(
                id=f.id,
                name=f.name,
                description=f.description or "",
                template_type=getattr(f, "template_type", None) or "verbatim-string",
                position=f.position,
            )
            for f in sorted(doc.schema_fields, key=lambda x: x.position)
        ],
    )


def resolve_run_documents(run: Run) -> list[SnapshotDocument]:
    snapshot = run.run_snapshot or {}
    raw_docs = snapshot.get("documents")
    if raw_docs:
        return [_document_from_snapshot(doc, idx) for idx, doc in enumerate(raw_docs)]
    workflow = run.workflow
    if not workflow:
        return []
    return [_document_from_orm(doc) for doc in sorted(workflow.documents, key=lambda d: d.position)]


def resolve_run_rules(run: Run, workflow: Workflow) -> list[dict]:
    snapshot = run.run_snapshot or {}
    raw_rules = snapshot.get("rules")
    if raw_rules:
        return [
            {
                "id": str(rule.get("id") or f"rule-{idx}"),
                "name": str(rule.get("name") or "Rule"),
                "kind": str(rule.get("kind") or "logic"),
                "scope": str(rule.get("scope") or "intra"),
                "applies_to": rule.get("applies_to") or rule.get("appliesTo") or [],
                "body": resolve_rule_body(
                    {
                        "body": rule.get("body") or "",
                        "conditions": rule.get("conditions"),
                        "condition_junction": rule.get("condition_junction")
                        or rule.get("conditionJunction"),
                    }
                ),
                "severity": str(rule.get("severity") or "reject"),
                "conditions": rule.get("conditions"),
                "condition_junction": rule.get("condition_junction")
                or rule.get("conditionJunction"),
            }
            for idx, rule in enumerate(raw_rules)
        ]
    return rules_payload(workflow)


def resolve_workflow_display_name(run: Run, workflow: Workflow) -> str:
    snapshot = run.run_snapshot or {}
    return str(snapshot.get("workflowName") or workflow.name or "Workflow")
