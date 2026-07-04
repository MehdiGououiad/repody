"""Build logic expressions from visual condition builder JSON (mirrors UI condition-builder)."""

from __future__ import annotations

import json
import re

NO_RIGHT = frozenset({"EXISTS", "IS_EMPTY"})


def _normalize_field_token(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def _field_ref(token: str) -> str | None:
    t = (token or "").strip()
    if not t:
        return None
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", t):
        return t
    if "." in t:
        parts = [_normalize_field_token(part) for part in t.split(".")]
        if all(re.match(r"^[a-z_][a-z0-9_]*$", part) for part in parts):
            return "__".join(parts) if len(parts) > 1 else parts[0]
    normalized = _normalize_field_token(t)
    if re.match(r"^[a-z_][a-z0-9_]*$", normalized):
        return normalized
    return None


def _literal_to_py(value: str) -> str | None:
    v = (value or "").strip()
    if not v:
        return None
    cleaned = v.replace(" ", "").replace(",", ".")
    try:
        if cleaned.replace(".", "", 1).replace("-", "", 1).isdigit() or re.match(
            r"^-?\d+\.?\d*$", cleaned
        ):
            return str(float(cleaned))
    except ValueError:
        pass
    return json.dumps(v)


def _operand_to_py(op: dict | None) -> str | None:
    if not op:
        return None
    if op.get("kind") == "literal":
        return _literal_to_py(str(op.get("value") or ""))
    return _field_ref(str(op.get("value") or ""))


def _list_literal_to_py(value: str) -> str | None:
    parts = [s.strip() for s in value.split(",") if s.strip()]
    if not parts:
        return None
    raw_items = [_literal_to_py(p) for p in parts]
    if any(i is None for i in raw_items):
        return None
    items = [item for item in raw_items if item is not None]
    return f"[{', '.join(items)}]"


def condition_to_string(condition: dict) -> str:
    left_base = _operand_to_py(condition.get("left"))
    if not left_base:
        return ""

    left = left_base
    if condition.get("arithmeticOp") and condition.get("leftExtra"):
        extra = _operand_to_py(condition.get("leftExtra"))
        if not extra:
            return ""
        left = f"({left_base} {condition['arithmeticOp']} {extra})"

    operator = condition.get("operator") or "=="
    if operator in NO_RIGHT:
        if operator == "EXISTS":
            return f'({left} is not None and str({left}).strip() not in ("", "—"))'
        return f'({left} is None or str({left}).strip() in ("", "—"))'

    right_op = condition.get("right")
    if not right_op:
        return ""

    if operator in ("IN", "NOT_IN"):
        joiner = "in" if operator == "IN" else "not in"
        if right_op.get("kind") == "literal" and "," in str(right_op.get("value") or ""):
            list_lit = _list_literal_to_py(str(right_op.get("value") or ""))
            if not list_lit:
                return ""
            return f"{left} {joiner} {list_lit}"
        right = _operand_to_py(right_op)
        if not right:
            return ""
        return f"{left} {joiner} {right}"

    right = _operand_to_py(right_op)
    if not right:
        return ""
    return f"{left} {operator} {right}"


def conditions_to_expression(
    conditions: list[dict] | None,
    junction: str = "AND",
) -> str:
    parts = [condition_to_string(c) for c in conditions or []]
    parts = [p for p in parts if p]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    j = (junction or "AND").upper()
    py_junction = "and" if j == "AND" else "or"
    return "(" + f") {py_junction} (".join(parts) + ")"


def resolve_rule_body(rule: dict) -> str:
    """Compile visual conditions when present; otherwise use stored body."""
    junction = rule.get("condition_junction") or rule.get("conditionJunction") or "AND"
    conditions = rule.get("conditions")
    if conditions:
        compiled = conditions_to_expression(conditions, str(junction))
        if compiled:
            return compiled
    return (rule.get("body") or "").strip()


def _condition_label(condition: dict, *, index: int) -> str:
    left = (condition.get("left") or {}).get("value") or ""
    op = condition.get("operator") or "=="
    right_op = condition.get("right") or {}
    right = right_op.get("value") or ""
    if op in NO_RIGHT:
        return f"{left} {op}".strip()
    if left and right:
        return f"{left} {op} {right}".strip()
    return f"Condition {index + 1}"


def logic_check_entries(rule: dict) -> list[dict]:
    """One validation check per visual condition (no combined AND/OR)."""
    conditions = rule.get("conditions") or []
    if not conditions:
        body = resolve_rule_body(rule)
        if not body:
            return []
        rid = rule.get("id") or "rule"
        return [
            {
                **rule,
                "id": rid,
                "body": body,
                "name": (rule.get("name") or "").strip() or "Rule",
            }
        ]

    base_name = (rule.get("name") or "").strip()
    entries: list[dict] = []
    for index, condition in enumerate(conditions):
        expression = condition_to_string(condition)
        if not expression:
            continue
        cid = str(condition.get("id") or index)
        label = _condition_label(condition, index=index)
        entries.append(
            {
                **rule,
                "id": f"{rule.get('id') or 'rule'}-c{cid}",
                "body": expression,
                "name": f"{base_name}: {label}" if base_name else label,
                "conditions": [condition],
            }
        )
    return entries


def expand_rules_for_evaluation(rules: list[dict]) -> list[dict]:
    """Logic rules with multiple conditions become one check each; LLM rules pass through."""
    expanded: list[dict] = []
    for rule in rules:
        kind = (rule.get("kind") or "logic").lower()
        if kind == "llm":
            expanded.append(rule)
            continue
        checks = logic_check_entries(rule)
        expanded.extend(checks if checks else [rule])
    return expanded
