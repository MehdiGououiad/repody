"""Workflow rule and document schema validation."""

from __future__ import annotations

import re
from dataclasses import dataclass

from repody.rules.conditions import NO_RIGHT, condition_to_string, resolve_rule_body
from repody.rules.rule_syntax import validate_logic_rule_body
from repody.rules.types import rule_kind
from repody.schemas.workflow import DocumentDefSchema, WorkflowRuleSchema, WorkflowSchema
from repody.util.json_shape import normalize_keys_to_snake


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
                f"{doc_label}: duplicate field name(s) {joined}. "
                "Each field name must be unique (case-insensitive)."
            )


def validate_workflow_rules(payload: WorkflowSchema) -> None:
    """Raise ValueError when any rule fails validation."""
    for rule in payload.rules:
        issues = validate_workflow_rule(rule)
        if issues:
            raise ValueError("; ".join(issues))


def _document_type(doc: DocumentDefSchema | dict) -> str:
    if isinstance(doc, dict):
        fields = normalize_keys_to_snake(doc)
        return str(fields.get("document_type") or "")
    return doc.document_type or ""


def _condition_incomplete(condition: dict) -> bool:
    left = condition.get("left") or {}
    if not str(left.get("value") or "").strip():
        return True
    operator = condition.get("operator") or "=="
    if operator in NO_RIGHT:
        return False
    right = condition.get("right") or {}
    return not str(right.get("value") or "").strip()


def _validate_logic_rule_conditions(rule: WorkflowRuleSchema | dict) -> list[str]:
    conditions = (
        rule.conditions if isinstance(rule, WorkflowRuleSchema) else rule.get("conditions") or []
    )
    rule_dict = (
        rule.model_dump(by_alias=False) if isinstance(rule, WorkflowRuleSchema) else dict(rule)
    )
    if not conditions:
        return ["Add at least one condition."]
    if any(_condition_incomplete(condition) for condition in conditions):
        return ["Complete every condition (field, operator, and value)."]
    expression = resolve_rule_body(rule_dict)
    if not expression:
        return ["Could not build an expression from these conditions."]
    if re.search(r"\b(AND|OR)\b", expression):
        return ["Expression uses invalid AND/OR — save again to recompile."]
    err = validate_logic_rule_body(expression)
    return [err] if err else []


def validate_workflow_rule(
    rule: WorkflowRuleSchema | dict,
) -> list[str]:
    """Return user-facing validation errors for one workflow rule."""
    if isinstance(rule, WorkflowRuleSchema):
        kind = (rule.kind or "logic").lower()
        label = (rule.name or "").strip() or rule.id or "Rule"
    else:
        fields = normalize_keys_to_snake(rule)
        kind = rule_kind(fields)
        label = (fields.get("name") or "").strip() or fields.get("id") or "Rule"

    if kind != "logic":
        return [f"{label}: only logic rules are supported."]

    issues = _validate_logic_rule_conditions(rule)
    return [f"{label}: {issue}" if not issue.startswith(label) else issue for issue in issues]


@dataclass(frozen=True, slots=True)
class RulePreview:
    """Validation outcome for one rule in the builder preview.

    `checks` is the compiled expression of each condition, in order ("" while incomplete).
    """

    rule_id: str
    issues: list[str]
    checks: list[str]


def validate_rules_preview(rules: list[WorkflowRuleSchema]) -> list[RulePreview]:
    """Validate all rules for builder preview - one result per rule id."""
    return [
        RulePreview(
            rule_id=rule.id,
            issues=validate_workflow_rule(rule),
            checks=[condition_to_string(c) for c in rule.conditions or []],
        )
        for rule in rules
    ]
