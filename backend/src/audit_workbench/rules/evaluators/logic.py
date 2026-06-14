from __future__ import annotations

from collections.abc import Awaitable, Callable

from audit_workbench.rules.conditions import expand_rules_for_evaluation
from audit_workbench.rules.evaluators.base import RuleEvaluator
from audit_workbench.rules.logic_evaluator import evaluate_logic_expression
from audit_workbench.rules.types import RuleEvalResult, collect_affected_fields


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


class LogicRuleEvaluator(RuleEvaluator):
    kind = "logic"

    async def evaluate_rules(
        self,
        rules: list[dict],
        field_values: dict[str, str],
        *,
        on_rule_start: Callable[[dict], Awaitable[None]] | None = None,
        llm_model: str | None = None,
    ) -> list[RuleEvalResult]:
        _ = llm_model
        results: list[RuleEvalResult] = []
        for rule in expand_rules_for_evaluation(rules):
            if on_rule_start is not None:
                await on_rule_start(rule)
            results.append(evaluate_logic_rule(rule, field_values))
        return results
