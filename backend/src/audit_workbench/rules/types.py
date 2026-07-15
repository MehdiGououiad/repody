from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RuleEvalResult:
    id: str
    name: str
    kind: str
    scope: str
    status: str
    severity: str
    expression: str
    affected_fields: list[str]
    detail: str
    expected_value: str | None = None
    actual_value: str | None = None


def rule_kind(rule: dict) -> str:
    return (rule.get("kind") or "logic").lower()


def rule_applies_to(rule: dict) -> list[str]:
    """Read applies_to from snake_case rule dicts (normalized snapshots / ORM helpers)."""
    raw = rule.get("applies_to") or []
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw]


def collect_affected_fields(rule: dict) -> list[str]:
    affected: list[str] = []
    for cond in rule.get("conditions") or []:
        for side in ("left", "left_extra", "right"):
            op = cond.get(side)
            if op and op.get("kind") == "field" and op.get("value"):
                affected.append(op["value"])
    if rule_kind(rule) == "llm":
        from audit_workbench.rules.llm_fields import referenced_fields

        affected.extend(referenced_fields(rule.get("body") or ""))
    return list(dict.fromkeys(affected))
