"""Workflow rule and schema validation."""

from __future__ import annotations

from audit_workbench.rules.conditions import resolve_rule_body
from audit_workbench.rules.validation import validate_rule_dict
from audit_workbench.schemas.workflow import WorkflowSchema


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
