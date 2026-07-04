from __future__ import annotations

import re
from typing import Any

from simpleeval import EvalWithCompoundTypes, simple_eval

from audit_workbench.extraction.field_json import parse_numeric_value
from audit_workbench.rules.types import RuleEvalResult, collect_affected_fields

_IDENTIFIER = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")
_RESERVED = {
    "and",
    "or",
    "not",
    "True",
    "False",
    "None",
    "if",
    "else",
    "in",
    "is",
    "str",
}


def _normalize_key(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def _strip_string_literals(expression: str) -> str:
    """Remove quoted literals so comparison values are not treated as field names."""
    without_double = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', ' "" ', expression)
    return re.sub(r"'[^'\\]*(?:\\.[^'\\]*)*'", " '' ", without_double)


def _identifiers_in_expression(expression: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for token in _IDENTIFIER.findall(_strip_string_literals(expression)):
        if token in _RESERVED:
            continue
        if token not in seen:
            seen.add(token)
            out.append(token)
    return out


def _lookup_field(names: dict[str, Any], ident: str) -> tuple[bool, Any]:
    """Return (present, value) for a field token used in an expression."""
    norm = _normalize_key(ident)
    if ident in names:
        return True, names[ident]
    if norm in names:
        return True, names[norm]
    return False, None


def coerce_field_value(raw: str) -> Any:
    text = (raw or "").strip()
    if not text or text == "—":
        return None
    numeric = parse_numeric_value(text)
    if numeric is not None:
        return numeric
    lowered = text.lower()
    if lowered in ("true", "false"):
        return lowered == "true"
    return text


def build_field_namespace(field_values: dict[str, str]) -> dict[str, Any]:
    namespace: dict[str, Any] = {}
    for key, value in field_values.items():
        norm = _normalize_key(key)
        coerced = coerce_field_value(value)
        namespace[norm] = coerced
        namespace[key] = coerced
        if "." in key:
            alias = key.replace(".", "__")
            namespace[alias] = coerced
            namespace[_normalize_key(alias)] = coerced
    return namespace


def evaluate_logic_expression(
    body: str, field_values: dict[str, str]
) -> tuple[bool | None, str, list[str]]:
    """Evaluate a logic rule. Returns (passed, detail, affected). passed=None means skipped."""
    expression = (body or "").strip()
    if not expression:
        return None, "Rule has no expression — skipped.", []

    names = build_field_namespace(field_values)
    referenced = _identifiers_in_expression(expression)

    missing: list[str] = []
    empty: list[str] = []
    for ident in referenced:
        present, value = _lookup_field(names, ident)
        if not present:
            missing.append(ident)
        elif value is None:
            empty.append(ident)

    if missing:
        label = ", ".join(missing)
        return (
            None,
            f"Field(s) not found: {label}. Check the name matches your schema fields.",
            missing,
        )
    if empty:
        label = ", ".join(empty)
        return (
            None,
            f"No value yet for {label}. Run OCR or enter a sample value in dry-run.",
            empty,
        )

    affected = [k for k, v in names.items() if v is not None and k == _normalize_key(k)]

    try:
        evaluator = EvalWithCompoundTypes()
        result = bool(simple_eval(expression, names=names, functions=evaluator.functions))
        if result:
            return True, "All conditions satisfied on the extracted values.", affected
        return False, f"Expression evaluated to false: {expression}", affected
    except Exception as exc:
        return False, f"Could not evaluate expression: {exc}", affected


def evaluate_logic_rule(rule: dict, field_values: dict[str, str]) -> RuleEvalResult:
    body = (rule.get("body") or "").strip()
    rule_id = rule.get("id") or ""
    name = rule.get("name") or "Rule"
    severity = rule.get("severity") or "reject"
    scope = rule.get("scope") or "intra"
    affected = collect_affected_fields(rule)

    if not body:
        return RuleEvalResult(
            id=rule_id,
            name=name,
            kind="logic",
            scope=scope,
            status="skipped",
            severity=severity,
            expression=body,
            affected_fields=affected,
            detail="Rule has no expression — configure conditions or a logic body.",
            expected_value=None,
            actual_value=None,
        )

    passed, detail, logic_affected = evaluate_logic_expression(body, field_values)
    if logic_affected:
        affected = list(dict.fromkeys(affected + logic_affected))
    if passed is None:
        status = "skipped"
    elif passed:
        status = "passed"
    else:
        status = "failed"

    return RuleEvalResult(
        id=rule_id,
        name=name,
        kind="logic",
        scope=scope,
        status=status,
        severity=severity,
        expression=body,
        affected_fields=affected,
        detail=detail,
        expected_value=None,
        actual_value=None,
    )
