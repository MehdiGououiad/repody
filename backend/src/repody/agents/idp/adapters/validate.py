"""Validation adapter — ExtractionOutput → ValidationOutput via rules.runner."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from repody.agents.idp.adapters.mapping import rule_result_from_eval
from repody.agents.idp.contracts import ExtractionOutput, RuleResult, ValidationOutput
from repody.extraction.modes import ValidationMode
from repody.rules.field_namespace import field_values_from_extractions
from repody.rules.runner import (
    evaluate_rules,
    rules_for_validation,
    skipped_llm_results,
)

_PASS = frozenset({"pass", "passed"})
_FAIL = frozenset({"fail", "failed", "error"})


def field_rows_from_extraction(
    extraction: ExtractionOutput,
    labels: dict[str, str],
) -> list[tuple[str, str, str | None]]:
    rows: list[tuple[str, str, str | None]] = []
    for doc in extraction.by_document:
        doc_type = labels.get(doc.document_id)
        for field in doc.fields:
            if not field.key:
                continue
            value = field.value if field.extracted and field.value else "—"
            rows.append((field.key, value, doc_type))
    return rows


def summarize_validation(results: tuple[RuleResult, ...] | list[RuleResult]) -> ValidationOutput:
    rows = tuple(results)
    passed = sum(1 for r in rows if r.status in _PASS)
    failed = sum(1 for r in rows if r.status in _FAIL)
    has_reject = any(r.status in _FAIL and r.severity == "reject" for r in rows)
    if failed == 0:
        overall = "passed"
    elif has_reject:
        overall = "failed"
    else:
        overall = "warning"
    return ValidationOutput(
        rule_results=rows,
        overall_status=overall,
        summary_passed=passed,
        summary_failed=failed,
    )


async def validate_extraction(
    extraction: ExtractionOutput,
    *,
    rules: list[dict],
    labels: dict[str, str],
    multi_document: bool,
    validation_mode: ValidationMode,
    on_rule_start: Callable[[dict], Awaitable[None]] | None = None,
    llm_model: str | None = None,
) -> ValidationOutput:
    """Turn frozen extraction into summarized validation (one rules-engine path)."""
    rows = field_rows_from_extraction(extraction, labels)
    field_values = field_values_from_extractions(rows, multi_document=multi_document)
    active_rules, skipped_rules = rules_for_validation(rules, validation_mode)
    rule_evals = await evaluate_rules(
        active_rules,
        field_values,
        extraction_rows=rows,
        doc_types_by_id=labels,
        multi_document=multi_document,
        on_rule_start=on_rule_start,
        llm_model=llm_model,
    )
    rule_evals.extend(skipped_llm_results(skipped_rules))
    return summarize_validation(tuple(rule_result_from_eval(row) for row in rule_evals))
