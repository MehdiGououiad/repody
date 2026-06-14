from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from audit_workbench.rules.conditions import expand_rules_for_evaluation
from audit_workbench.rules.evaluators.logic import evaluate_logic_rule
from audit_workbench.rules.llm_evaluator import RuleStatus, evaluate_llm_rule, evaluate_llm_rules_batch
from audit_workbench.rules.types import RuleEvalResult, collect_affected_fields


async def evaluate_rules(
    rules: list[dict],
    field_values: dict[str, str],
    *,
    on_rule_start: Callable[[dict], Awaitable[None]] | None = None,
    llm_model: str | None = None,
    precomputed_llm: dict[str, tuple[RuleStatus, str]] | None = None,
) -> list[RuleEvalResult]:
    expanded = expand_rules_for_evaluation(rules)
    llm_rules = [r for r in rules if (r.get("kind") or "logic").lower() == "llm"]
    precomputed = precomputed_llm or {}
    remaining_llm = [r for r in llm_rules if (r.get("id") or "") not in precomputed]

    llm_task: asyncio.Task[dict[str, tuple[RuleStatus, str]]] | None = None
    if remaining_llm:
        llm_task = asyncio.create_task(
            evaluate_llm_rules_batch(remaining_llm, field_values, llm_model=llm_model)
        )

    results: list[RuleEvalResult] = []
    for rule in expanded:
        kind = (rule.get("kind") or "logic").lower()
        if on_rule_start is not None and kind == "llm":
            await on_rule_start(rule)
        rule_id = rule.get("id") or ""

        if kind == "llm":
            body = (rule.get("body") or "").strip()
            name = rule.get("name") or "Rule"
            if rule_id in precomputed:
                status, detail = precomputed[rule_id]
            elif llm_task is not None:
                llm_results = await llm_task
                if rule_id in llm_results:
                    status, detail = llm_results[rule_id]
                else:
                    status, detail = "error", "LLM batch did not return a result for this rule."
            else:
                status, detail = await evaluate_llm_rule(
                    body, field_values, rule_name=name, llm_model=llm_model
                )
            results.append(
                RuleEvalResult(
                    id=rule_id,
                    name=name,
                    kind=kind,
                    scope=rule.get("scope") or "intra",
                    status=status,
                    severity=rule.get("severity") or "reject",
                    expression=body,
                    affected_fields=collect_affected_fields(rule),
                    detail=detail,
                    expected_value=None,
                    actual_value=None,
                )
            )
        else:
            results.append(evaluate_logic_rule(rule, field_values))

    return results
