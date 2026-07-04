"""Workflow rule and document schema validation."""

from __future__ import annotations

from audit_workbench.rules.conditions import resolve_rule_body
from audit_workbench.rules.rule_syntax import validate_rule_dict
from audit_workbench.schemas.workflow import DocumentDefSchema, WorkflowSchema


def normalize_schema_field_name(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def duplicate_field_names(fields: list) -> list[str]:
    """Return display names of fields that collide case-insensitively."""
    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for field in fields:
        raw = getattr(field, "name", None) or (field.get("name") if isinstance(field, dict) else "")
        name = str(raw or "").strip()
        norm = normalize_schema_field_name(name)
        if not norm:
            continue
        if norm in seen:
            label = name or seen[norm]
            if label not in duplicates:
                duplicates.append(label)
        else:
            seen[norm] = name
    return duplicates


def validate_workflow_schema(payload: WorkflowSchema) -> None:
    """Raise ValueError when document schemas are invalid."""
    for doc in payload.documents:
        doc_label = (doc.document_type or "").strip() or "Document"
        dupes = duplicate_field_names(doc.schema_fields)
        if dupes:
            joined = ", ".join(f'"{name}"' for name in dupes)
            raise ValueError(
                f'{doc_label}: duplicate field name(s) {joined}. '
                "Each field name must be unique (case-insensitive)."
            )


def validate_document_schema(doc: DocumentDefSchema) -> list[str]:
    """Return user-facing errors for a single document schema."""
    dupes = duplicate_field_names(doc.schema_fields)
    if not dupes:
        return []
    joined = ", ".join(f'"{name}"' for name in dupes)
    doc_label = (doc.document_type or "").strip() or "Document"
    return [
        f'{doc_label}: duplicate field name(s) {joined}. '
        "Each field name must be unique (case-insensitive)."
    ]


def validate_workflow_rules(payload: WorkflowSchema) -> None:
    """Raise ValueError when any rule fails validation."""
    for rule in payload.rules:
        resolved_body = resolve_rule_body(
            {
                "body": rule.body,
                "conditions": rule.conditions,
                "condition_junction": rule.condition_junction,
            }
        )
        rule_errors = validate_rule_dict(
            {
                "id": rule.id,
                "name": rule.name,
                "kind": rule.kind,
                "body": resolved_body,
            }
        )
        if rule_errors:
            raise ValueError("; ".join(rule_errors))


def validate_rule_preview(rule: dict) -> list[str]:
    """Return validation errors for a single rule dict (API + client preview)."""
    resolved_body = resolve_rule_body(rule)
    return validate_rule_dict(
        {
            "id": rule.get("id"),
            "name": rule.get("name"),
            "kind": rule.get("kind"),
            "body": resolved_body,
        }
    )
