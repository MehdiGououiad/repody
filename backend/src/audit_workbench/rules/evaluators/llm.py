from __future__ import annotations

from collections.abc import Awaitable, Callable

from audit_workbench.rules.evaluators.base import RuleEvaluator
from audit_workbench.rules.llm_evaluator import evaluate_llm_rule, evaluate_llm_rules_batch
from audit_workbench.rules.types import RuleEvalResult, collect_affected_fields


class LlmRuleEvaluator(RuleEvaluator):
    kind = "llm"

    async def evaluate_rules(
        self,
        rules: list[dict],
        field_values: dict[str, str],
        *,
        on_rule_start: Callable[[dict], Awaitable[None]] | None = None,
        llm_model: str | None = None,
    ) -> list[RuleEvalResult]:
        llm_results = await evaluate_llm_rules_batch(
            rules, field_values, llm_model=llm_model
        )
        results: list[RuleEvalResult] = []
        for rule in rules:
            if on_rule_start is not None:
                await on_rule_start(rule)
            body = (rule.get("body") or "").strip()
            rule_id = rule.get("id") or ""
            name = rule.get("name") or "Rule"
            severity = rule.get("severity") or "reject"
            scope = rule.get("scope") or "intra"
            affected = collect_affected_fields(rule)

            status, detail = llm_results.get(
                rule_id,
                await evaluate_llm_rule(body, field_values, rule_name=name, llm_model=llm_model),
            )

            results.append(
                RuleEvalResult(
                    id=rule_id,
                    name=name,
                    kind=self.kind,
                    scope=scope,
                    status=status,
                    severity=severity,
                    expression=body,
                    affected_fields=affected,
                    detail=detail,
                    expected_value=None,
                    actual_value=None,
                )
            )
        return results
