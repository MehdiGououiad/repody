from __future__ import annotations

from collections.abc import Awaitable, Callable

from repody.rules.conditions import expand_rules_for_evaluation, resolve_rule_body
from repody.rules.field_namespace import (
    field_values_for_rule,
    field_values_from_extractions,
)
from repody.rules.logic_evaluator import evaluate_logic_rule
from repody.rules.types import RuleEvalResult, collect_affected_fields, rule_kind


def _unsupported_result(rule: dict) -> RuleEvalResult:
    """Rules of a kind other than ``logic`` (legacy ``llm`` rules) are reported, not run."""
    return RuleEvalResult(
        id=rule.get("id") or "",
        name=rule.get("name") or "Rule",
        kind=rule_kind(rule),
        scope=rule.get("scope") or "intra",
        status="skipped",
        severity=rule.get("severity") or "reject",
        expression=rule.get("body") or "",
        affected_fields=collect_affected_fields(rule),
        detail="Skipped — only logic rules are evaluated.",
    )


async def validate_field_rows(
    rows: list[tuple[str, str, str | None]],
    rules: list[dict],
    *,
    doc_types_by_id: dict[str, str],
    multi_document: bool,
    on_rule_start: Callable[[dict], Awaitable[None]] | None = None,
) -> list[RuleEvalResult]:
    """Evaluate workflow rules over extracted ``(key, value, document type)`` rows."""
    field_values = field_values_from_extractions(rows, multi_document=multi_document)
    return await evaluate_rules(
        rules,
        field_values,
        extraction_rows=rows,
        doc_types_by_id=doc_types_by_id,
        multi_document=multi_document,
        on_rule_start=on_rule_start,
    )


async def evaluate_rules(
    rules: list[dict],
    field_values: dict[str, str],
    *,
    extraction_rows: list[tuple[str, str, str | None]] | None = None,
    doc_types_by_id: dict[str, str] | None = None,
    multi_document: bool = False,
    on_rule_start: Callable[[dict], Awaitable[None]] | None = None,
) -> list[RuleEvalResult]:
    results: list[RuleEvalResult] = []
    for rule in expand_rules_for_evaluation(rules):
        if on_rule_start is not None:
            await on_rule_start(rule)
        if rule_kind(rule) != "logic":
            results.append(_unsupported_result(rule))
            continue
        scoped_values = field_values
        if extraction_rows is not None and doc_types_by_id:
            scoped_values = field_values_for_rule(
                extraction_rows,
                rule,
                doc_types_by_id=doc_types_by_id,
                multi_document=multi_document,
            )
        results.append(
            evaluate_logic_rule({**rule, "body": resolve_rule_body(rule)}, scoped_values)
        )
    return results


async def evaluate_dry_run_rules(
    rules: list[dict],
    field_values: dict[str, str] | None = None,
) -> list[dict]:
    evals = await evaluate_rules(rules, field_values or {})
    return [
        {"id": r.id, "name": r.name, "kind": r.kind, "status": r.status, "detail": r.detail}
        for r in evals
    ]
