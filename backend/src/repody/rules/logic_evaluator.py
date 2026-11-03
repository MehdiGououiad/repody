"""Evaluate one logic rule against extracted field values."""

from __future__ import annotations

from typing import Any

from repody.rules.amounts import parse_numeric_value
from repody.rules.expression import evaluate, field_key, referenced_names
from repody.rules.types import RuleEvalResult, collect_affected_fields
from repody.rules.value_coercion import MISSING, is_iso_date_like


def coerce_field_value(raw: str) -> Any:
    """Extracted text as the rule sees it: None (missing), ISO date text, number, bool or text."""
    text = (raw or "").strip()
    if not text or text == MISSING:
        return None
    if is_iso_date_like(text):
        return text
    numeric = parse_numeric_value(text)
    if numeric is not None:
        return numeric
    if text.lower() in ("true", "false"):
        return text.lower() == "true"
    return text


def evaluate_logic_expression(
    body: str, field_values: dict[str, str]
) -> tuple[bool | None, str, list[str]]:
    """``(passed, detail, fields_used)``; ``passed`` is None when the rule is skipped."""
    expression = (body or "").strip()
    if not expression:
        return None, "Rule has no expression — skipped.", []
    try:
        used = referenced_names(expression)
    except SyntaxError as exc:
        return False, f"Could not evaluate expression: {exc.msg}", []

    values = {field_key(key): coerce_field_value(value) for key, value in field_values.items()}
    affected = [field_key(name) for name in used]
    missing = [name for name in used if field_key(name) not in values]
    if missing:
        return (
            None,
            f"Field(s) not found: {', '.join(missing)}. Check the name matches your schema fields.",
            affected,
        )
    empty = [name for name in used if values[field_key(name)] is None]
    if empty:
        return (
            None,
            f"No value yet for {', '.join(empty)}. Run a test extraction or enter a sample "
            "value in dry-run.",
            affected,
        )
    try:
        passed = bool(evaluate(expression, {name: values[field_key(name)] for name in used}))
    except Exception as exc:
        return False, f"Could not evaluate expression: {exc}", affected
    if passed:
        return True, "All conditions satisfied on the extracted values.", affected
    return False, f"Expression evaluated to false: {expression}", affected


def evaluate_logic_rule(rule: dict, field_values: dict[str, str]) -> RuleEvalResult:
    body = (rule.get("body") or "").strip()
    if body:
        passed, detail, used = evaluate_logic_expression(body, field_values)
        status = "skipped" if passed is None else "passed" if passed else "failed"
    else:
        used, status = [], "skipped"
        detail = "Rule has no expression — configure conditions or a logic body."
    return RuleEvalResult(
        id=rule.get("id") or "",
        name=rule.get("name") or "Rule",
        kind="logic",
        scope=rule.get("scope") or "intra",
        status=status,
        severity=rule.get("severity") or "reject",
        expression=body,
        affected_fields=list(dict.fromkeys([*collect_affected_fields(rule), *used])),
        detail=detail,
    )
