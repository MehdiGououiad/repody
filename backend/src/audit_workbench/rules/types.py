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


def collect_affected_fields(rule: dict) -> list[str]:
    affected: list[str] = []
    for cond in rule.get("conditions") or []:
        for side in ("left", "leftExtra", "right"):
            op = cond.get(side)
            if op and op.get("kind") == "field" and op.get("value"):
                affected.append(op["value"])
    if (rule.get("kind") or "logic").lower() == "llm":
        from audit_workbench.rules.llm_fields import referenced_fields

        affected.extend(referenced_fields(rule.get("body") or ""))
    return list(dict.fromkeys(affected))
