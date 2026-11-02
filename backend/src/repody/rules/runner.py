from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from repody.extraction.modes import (
    LOGIC_VALIDATION,
    RUN_VALIDATION_LLM,
    ValidationMode,
)
from repody.rules.conditions import expand_rules_for_evaluation, resolve_rule_body
from repody.rules.field_namespace import (
    field_values_for_rule,
    field_values_from_extractions,
)
from repody.rules.llm_evaluator import (
    RuleStatus,
    evaluate_llm_rule,
    evaluate_llm_rules_batch,
)
from repody.rules.logic_evaluator import evaluate_logic_rule
from repody.rules.types import RuleEvalResult, collect_affected_fields, rule_kind


def rules_for_validation(
    rules: list[dict],
    validation_mode: ValidationMode,
) -> tuple[list[dict], list[dict]]:
    """Split active rules vs LLM rules skipped on logic-only paths."""
    active: list[dict] = []
    skipped: list[dict] = []
    for rule in rules:
        kind = rule_kind(rule)
        if validation_mode == LOGIC_VALIDATION and kind == "llm":
            skipped.append(rule)
        else:
            active.append(rule)
    return active, skipped


def skipped_llm_results(skipped: list[dict]) -> list[RuleEvalResult]:
    out: list[RuleEvalResult] = []
    for rule in skipped:
        out.append(
            RuleEvalResult(
                id=rule.get("id") or "",
                name=rule.get("name") or "Rule",
                kind="llm",
                scope=rule.get("scope") or "intra",
                status="skipped",
                severity=rule.get("severity") or "reject",
                expression=rule.get("body") or "",
                affected_fields=collect_affected_fields(rule),
                detail="Skipped — processing path uses logic rules only.",
            )
        )
    return out


async def validate_field_rows(
    rows: list[tuple[str, str, str | None]],
    rules: list[dict],
    *,
    doc_types_by_id: dict[str, str],
    multi_document: bool,
    validation_mode: ValidationMode = RUN_VALIDATION_LLM,
    on_rule_start: Callable[[dict], Awaitable[None]] | None = None,
    llm_model: str | None = None,
) -> list[RuleEvalResult]:
    """Evaluate workflow rules over extracted ``(key, value, document type)`` rows.

    LLM rules on a logic-only validation path come back as ``skipped`` results.
    """
    field_values = field_values_from_extractions(rows, multi_document=multi_document)
    active_rules, skipped_rules = rules_for_validation(rules, validation_mode)
    results = await evaluate_rules(
        active_rules,
        field_values,
        extraction_rows=rows,
        doc_types_by_id=doc_types_by_id,
        multi_document=multi_document,
        on_rule_start=on_rule_start,
        llm_model=llm_model,
    )
    results.extend(skipped_llm_results(skipped_rules))
    return results


async def evaluate_rules(
    rules: list[dict],
    field_values: dict[str, str],
    *,
    extraction_rows: list[tuple[str, str, str | None]] | None = None,
    doc_types_by_id: dict[str, str] | None = None,
    multi_document: bool = False,
    on_rule_start: Callable[[dict], Awaitable[None]] | None = None,
    llm_model: str | None = None,
) -> list[RuleEvalResult]:
    expanded = expand_rules_for_evaluation(rules)
    llm_rules = [r for r in rules if rule_kind(r) == "llm"]

    llm_task: asyncio.Task[dict[str, tuple[RuleStatus, str]]] | None = None
    if llm_rules:
        llm_task = asyncio.create_task(
            evaluate_llm_rules_batch(llm_rules, field_values, llm_model=llm_model)
        )

    results: list[RuleEvalResult] = []
    for rule in expanded:
        kind = rule_kind(rule)
        if on_rule_start is not None:
            await on_rule_start(rule)
        rule_id = rule.get("id") or ""

        if kind == "llm":
            body = (rule.get("body") or "").strip()
            name = rule.get("name") or "Rule"
            if llm_task is not None:
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
            scoped_values = field_values
            if extraction_rows is not None and doc_types_by_id:
                scoped_values = field_values_for_rule(
                    extraction_rows,
                    rule,
                    doc_types_by_id=doc_types_by_id,
                    multi_document=multi_document,
                )
            logic_rule = {**rule, "body": resolve_rule_body(rule)}
            results.append(evaluate_logic_rule(logic_rule, scoped_values))

    return results


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
