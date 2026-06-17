from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from audit_workbench.extraction.base import ExtractionResult
from audit_workbench.extraction.document_modes import (
    LOGIC_VALIDATION,
    RUN_VALIDATION_LLM,
    ValidationMode,
)
from audit_workbench.rules.conditions import expand_rules_for_evaluation, resolve_rule_body
from audit_workbench.rules.llm_evaluator import (
    RuleStatus,
    evaluate_llm_rule,
    evaluate_llm_rules_batch,
)
from audit_workbench.rules.logic_evaluator import evaluate_logic_rule
from audit_workbench.rules.types import RuleEvalResult, collect_affected_fields
from audit_workbench.services.field_namespace import (
    field_values_for_rule,
    field_values_from_extractions,
)


def rules_for_validation(
    rules: list[dict],
    validation_mode: ValidationMode,
) -> tuple[list[dict], list[dict]]:
    """Split active rules vs LLM rules skipped on logic-only paths."""
    active: list[dict] = []
    skipped: list[dict] = []
    for rule in rules:
        kind = (rule.get("kind") or "logic").lower()
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


async def validate_extractions(
    *,
    extractions: list[tuple[str, ExtractionResult]],
    rules: list[dict],
    multi_document: bool,
    validation_mode: ValidationMode = RUN_VALIDATION_LLM,
    on_rule_start: Callable[[dict], Awaitable[None]] | None = None,
    llm_model: str | None = None,
    precomputed_llm: dict[str, tuple[str, str]] | None = None,
    doc_types_by_id: dict[str, str] | None = None,
) -> tuple[dict[str, str], list[RuleEvalResult]]:
    """Validate extracted fields against workflow rules."""
    rows: list[tuple[str, str, str | None]] = []
    for doc_type, result in extractions:
        for field in result.fields:
            if not field.key:
                continue
            value = field.value if field.extracted and field.value else "—"
            rows.append((field.key, value, doc_type))

    field_values = field_values_from_extractions(rows, multi_document=multi_document)
    active_rules, skipped_rules = rules_for_validation(rules, validation_mode)

    rule_results = await evaluate_rules(
        active_rules,
        field_values,
        extraction_rows=rows,
        doc_types_by_id=doc_types_by_id or {},
        multi_document=multi_document,
        on_rule_start=on_rule_start,
        llm_model=llm_model,
        precomputed_llm=precomputed_llm,
    )
    rule_results.extend(skipped_llm_results(skipped_rules))
    return field_values, rule_results


async def evaluate_rules(
    rules: list[dict],
    field_values: dict[str, str],
    *,
    extraction_rows: list[tuple[str, str, str | None]] | None = None,
    doc_types_by_id: dict[str, str] | None = None,
    multi_document: bool = False,
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
