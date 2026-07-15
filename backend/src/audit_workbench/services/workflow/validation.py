"""Workflow rule and document schema validation."""

from __future__ import annotations

import re

from audit_workbench.catalog.registry import normalize_model_id
from audit_workbench.extraction.document_model_branding import UnknownCatalogIdError
from audit_workbench.rules.conditions import NO_RIGHT, resolve_rule_body
from audit_workbench.rules.llm_fields import referenced_fields
from audit_workbench.rules.rule_syntax import validate_llm_rule_body, validate_logic_rule_body
from audit_workbench.rules.types import rule_applies_to, rule_kind
from audit_workbench.schemas.workflow import DocumentDefSchema, WorkflowRuleSchema, WorkflowSchema
from audit_workbench.util.json_shape import normalize_keys_to_snake


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
        try:
            normalize_model_id(doc.document_model_id)
        except UnknownCatalogIdError as exc:
            raise ValueError(f"{doc_label}: {exc}") from exc


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
        issues = validate_workflow_rule(rule, payload.documents)
        if issues:
            raise ValueError("; ".join(issues))


def _schema_fields(doc: DocumentDefSchema | dict) -> list:
    if isinstance(doc, dict):
        doc = normalize_keys_to_snake(doc)
        return doc.get("schema_fields") or doc.get("schema") or []
    return doc.schema_fields


def _document_type(doc: DocumentDefSchema | dict) -> str:
    if isinstance(doc, dict):
        doc = normalize_keys_to_snake(doc)
        return str(doc.get("document_type") or "")
    return doc.document_type or ""


def resolve_document_field_tokens(
    documents: list[DocumentDefSchema],
    applies_to: list[str],
) -> list[str]:
    """Field tokens available to LLM rules — matches the workflow builder UI."""
    targets = (
        [doc for doc in documents if doc.id in applies_to]
        if applies_to
        else list(documents)
    )
    multi = len(documents) > 1
    tokens: list[str] = []
    for doc in targets:
        doc_token = normalize_schema_field_name(_document_type(doc))
        for field in _schema_fields(doc):
            raw_name = getattr(field, "name", None) or (
                field.get("name") if isinstance(field, dict) else ""
            )
            name = str(raw_name or "").strip()
            if not name:
                continue
            field_token = normalize_schema_field_name(name)
            tokens.append(f"{doc_token}.{field_token}" if multi else field_token)
    return tokens


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
        rule.conditions
        if isinstance(rule, WorkflowRuleSchema)
        else rule.get("conditions") or []
    )
    rule_dict = (
        rule.model_dump(by_alias=False)
        if isinstance(rule, WorkflowRuleSchema)
        else dict(rule)
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
    documents: list[DocumentDefSchema],
) -> list[str]:
    """Return user-facing validation errors for one workflow rule."""
    if isinstance(rule, WorkflowRuleSchema):
        kind = (rule.kind or "logic").lower()
        label = (rule.name or "").strip() or rule.id or "Rule"
        applies_to = rule.applies_to or []
        body = rule.body or ""
    else:
        rule = normalize_keys_to_snake(rule)
        kind = rule_kind(rule)
        label = (rule.get("name") or "").strip() or rule.get("id") or "Rule"
        applies_to = rule_applies_to(rule)
        body = rule.get("body") or ""

    if kind == "llm":
        text = (body or "").strip()
        if not text:
            return ["LLM prompt is empty."]
        available = set(resolve_document_field_tokens(documents, applies_to))
        unknown = [field for field in referenced_fields(text) if field not in available]
        if unknown:
            refs = ", ".join(f"@{field}" for field in unknown)
            plural = "references" if len(unknown) > 1 else "reference"
            return [f"Unknown field {plural}: {refs}."]
        err = validate_llm_rule_body(text)
        return [f"{label}: {err}"] if err else []

    issues = _validate_logic_rule_conditions(rule)
    return [f"{label}: {issue}" if not issue.startswith(label) else issue for issue in issues]


def validate_rules_preview(
    documents: list[DocumentDefSchema],
    rules: list[WorkflowRuleSchema],
) -> list[dict[str, object]]:
    """Validate all rules for builder preview — one result per rule id."""
    return [
        {
            "rule_id": rule.id,
            "issues": validate_workflow_rule(rule, documents),
        }
        for rule in rules
    ]
