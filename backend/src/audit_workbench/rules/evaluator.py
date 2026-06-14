from __future__ import annotations

from collections.abc import Awaitable, Callable

from audit_workbench.rules.runner import evaluate_rules as _evaluate_rules_async
from audit_workbench.rules.types import RuleEvalResult

__all__ = ["RuleEvalResult", "evaluate_rules", "evaluate_dry_run_rules"]


async def evaluate_rules(
    rules: list[dict],
    field_values: dict[str, str] | None = None,
    *,
    on_rule_start: Callable[[dict], Awaitable[None]] | None = None,
    llm_model: str | None = None,
    precomputed_llm: dict[str, tuple[str, str]] | None = None,
) -> list[RuleEvalResult]:
    return await _evaluate_rules_async(
        rules,
        field_values or {},
        on_rule_start=on_rule_start,
        llm_model=llm_model,
        precomputed_llm=precomputed_llm,
    )


async def evaluate_dry_run_rules(
    rules: list[dict],
    field_values: dict[str, str] | None = None,
) -> list[dict]:
    evals = await evaluate_rules(rules, field_values or {})
    return [
        {
            "id": r.id,
            "name": r.name,
            "kind": r.kind,
            "status": r.status,
            "detail": r.detail,
        }
        for r in evals
    ]
