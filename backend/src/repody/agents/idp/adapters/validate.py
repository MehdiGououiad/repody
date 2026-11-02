"""Validation adapter - ExtractionOutput -> ValidationOutput via rules.runner."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence

from repody.agents.idp.adapters.mapping import rule_result_from_eval
from repody.agents.idp.contracts import (
    ExtractionOutput,
    RuleResult,
    ValidationOutput,
)
from repody.extraction.modes import ValidationMode
from repody.rules.runner import validate_field_rows
from repody.rules.value_coercion import MISSING

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
            value = field.value if field.extracted and field.value else MISSING
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
    rules: Sequence[dict],
    labels: dict[str, str],
    multi_document: bool,
    validation_mode: ValidationMode,
    on_rule_start: Callable[[dict], Awaitable[None]] | None = None,
    llm_model: str | None = None,
) -> ValidationOutput:
    """Turn frozen extraction into summarized validation (one rules-engine path)."""
    rule_evals = await validate_field_rows(
        field_rows_from_extraction(extraction, labels),
        list(rules),
        doc_types_by_id=labels,
        multi_document=multi_document,
        validation_mode=validation_mode,
        on_rule_start=on_rule_start,
        llm_model=llm_model,
    )
    return summarize_validation(tuple(rule_result_from_eval(row) for row in rule_evals))
