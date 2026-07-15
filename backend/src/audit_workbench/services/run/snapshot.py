"""Ephemeral per-run workflow config (microservice boundary — no workflow mutation)."""

from __future__ import annotations

from dataclasses import dataclass, field

from audit_workbench.db.models import Document, Run, Workflow
from audit_workbench.extraction.document_modes import DEFAULT_READ_PATH_ID, normalize_document_modes
from audit_workbench.services.run.helpers import rule_dict_from_row, rules_payload
from audit_workbench.util.json_shape import normalize_keys_to_snake


@dataclass
class SnapshotSchemaField:
    id: str
    name: str
    description: str
    position: int
    template_type: str = "verbatim-string"
    field_config: dict | None = None


@dataclass
class SnapshotDocument:
    """Document view for run pipeline — ORM Document or snapshot JSON."""

    id: str
    document_type: str
    position: int
    extraction_mode: str
    validation_mode: str
    document_model_id: str | None
    extraction_instructions: str = ""
    markdown_extraction: bool = False
    extraction_icl_examples: list[dict] | None = None
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
        out["documents"] = [normalize_keys_to_snake(doc) for doc in documents]
    if rules:
        out["rules"] = [normalize_keys_to_snake(rule) for rule in rules]
    if workflow_name:
        out["workflow_name"] = workflow_name
    return out


def _schema_fields_from_snapshot(doc: dict) -> list[SnapshotSchemaField]:
    raw = doc.get("schema") or doc.get("schema_fields") or []
    fields: list[SnapshotSchemaField] = []
    for idx, field_row in enumerate(raw):
        if not isinstance(field_row, dict):
            continue
        name = (field_row.get("name") or "").strip()
        if not name:
            continue
        fields.append(
            SnapshotSchemaField(
                id=str(field_row.get("id") or f"sf-{idx}"),
                name=name,
                description=str(field_row.get("description") or ""),
                template_type=str(field_row.get("template_type") or "verbatim-string"),
                field_config=_field_config_from_snapshot_row(field_row),
                position=idx,
            )
        )
    return fields


def _field_config_from_snapshot_row(field_row: dict) -> dict | None:
    config: dict = {}
    enum_values = field_row.get("enum_values")
    if enum_values:
        config["enum_values"] = enum_values
    children = field_row.get("children")
    if children:
        config["children"] = children
    return config or None


def _document_from_snapshot(doc: dict, position: int) -> SnapshotDocument:
    doc = normalize_keys_to_snake(doc)
    read_id, val_id = normalize_document_modes(
        doc.get("extraction_mode"),
        doc.get("validation_mode"),
    )
    return SnapshotDocument(
        id=str(doc.get("id") or f"doc-{position}"),
        document_type=str(doc.get("document_type") or ""),
        position=position,
        extraction_mode=read_id,
        validation_mode=val_id,
        document_model_id=doc.get("document_model_id"),
        extraction_instructions=str(doc.get("extraction_instructions") or ""),
        markdown_extraction=bool(doc.get("markdown_extraction") or False),
        extraction_icl_examples=list(doc.get("extraction_icl_examples") or []),
        schema_fields=_schema_fields_from_snapshot(doc),
    )


def _document_from_orm(doc: Document) -> SnapshotDocument:
    return SnapshotDocument(
        id=doc.id,
        document_type=doc.document_type,
        position=doc.position,
        extraction_mode=doc.extraction_mode or DEFAULT_READ_PATH_ID,
        validation_mode=getattr(doc, "validation_mode", None) or "logic_only",
        document_model_id=doc.document_model_id,
        extraction_instructions=getattr(doc, "extraction_instructions", None) or "",
        markdown_extraction=bool(getattr(doc, "markdown_extraction", False)),
        extraction_icl_examples=list(getattr(doc, "extraction_icl_examples", None) or []),
        schema_fields=[
            SnapshotSchemaField(
                id=f.id,
                name=f.name,
                description=f.description or "",
                template_type=getattr(f, "template_type", None) or "verbatim-string",
                field_config=normalize_keys_to_snake(getattr(f, "field_config", None) or None),
                position=f.position,
            )
            for f in sorted(doc.schema_fields, key=lambda x: x.position)
        ],
    )


def resolve_run_documents(run: Run) -> list[SnapshotDocument]:
    snapshot = normalize_keys_to_snake(run.run_snapshot or {})
    raw_docs = snapshot.get("documents")
    if raw_docs:
        return [_document_from_snapshot(doc, idx) for idx, doc in enumerate(raw_docs)]
    workflow = run.workflow
    if not workflow:
        return []
    return [_document_from_orm(doc) for doc in sorted(workflow.documents, key=lambda d: d.position)]


def resolve_run_rules(run: Run, workflow: Workflow) -> list[dict]:
    snapshot = normalize_keys_to_snake(run.run_snapshot or {})
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
    return rules_payload(workflow)


def resolve_workflow_display_name(run: Run, workflow: Workflow) -> str:
    snapshot = normalize_keys_to_snake(run.run_snapshot or {})
    return str(snapshot.get("workflow_name") or workflow.name or "Workflow")
