from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Literal

from audit_workbench.extraction.base import ExtractionResult
from audit_workbench.extraction.processing_paths import ValidationKind
from audit_workbench.rules.evaluator import evaluate_rules
from audit_workbench.rules.types import RuleEvalResult, collect_affected_fields

ValidationMode = ValidationKind


def doc_field_prefix(document_type: str, *, multi_document: bool) -> str:
    """Token prefix for cross-document rules (matches workflow UI)."""
    if not multi_document:
        return ""
    slug = document_type.strip().lower().replace(" ", "_")
    return f"{slug}." if slug else ""


def field_values_from_extractions(
    rows: list[tuple[str, str, str | None]],
    *,
    multi_document: bool,
) -> dict[str, str]:
    """
    Build evaluator namespace from extracted rows.

    Each row is (key, value, document_type). When multiple documents exist,
    prefixed keys (e.g. contract.reference_id) are added alongside bare keys when unique.
    """
    values: dict[str, str] = {}
    bare_keys: dict[str, list[str]] = {}

    for key, value, doc_type in rows:
        if not key or not value:
            continue
        prefix = doc_field_prefix(doc_type or "", multi_document=multi_document)
        qualified = f"{prefix}{key}" if prefix else key
        values[qualified] = value
        norm_q = qualified.strip().lower().replace(" ", "_")
        values[norm_q] = value

        bare_keys.setdefault(key, []).append(value)
        if not prefix:
            values[key] = value
            norm = key.strip().lower().replace(" ", "_")
            values[norm] = value

    if multi_document:
        for key, vals in bare_keys.items():
            if len(vals) == 1:
                values[key] = vals[0]
                norm = key.strip().lower().replace(" ", "_")
                values[norm] = vals[0]

    return values


def rules_for_validation(
    rules: list[dict],
    validation_mode: ValidationMode,
) -> tuple[list[dict], list[dict]]:
    """Split active rules vs LLM rules skipped on logic-only paths."""
    active: list[dict] = []
    skipped: list[dict] = []
    for rule in rules:
        kind = (rule.get("kind") or "logic").lower()
        if validation_mode == "logic_only" and kind == "llm":
            skipped.append(rule)
        else:
            active.append(rule)
    return active, skipped


def _skipped_llm_results(skipped: list[dict]) -> list[RuleEvalResult]:
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


async def extract_and_validate(
    *,
    extractions: list[tuple[str, ExtractionResult]],
    rules: list[dict],
    multi_document: bool,
    validation_mode: ValidationMode = "logic_and_llm",
    on_rule_start: Callable[[dict], Awaitable[None]] | None = None,
    llm_model: str | None = None,
    precomputed_llm: dict[str, tuple[str, str]] | None = None,
) -> tuple[dict[str, str], list[RuleEvalResult]]:
    """
    Single validation pass after extraction.

    Logic rules: expressions on extracted field values (instant).
    LLM rules: batched call, or precomputed from combined extract+validate step.
    """
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
        on_rule_start=on_rule_start,
        llm_model=llm_model,
        precomputed_llm=precomputed_llm,
    )
    rule_results.extend(_skipped_llm_results(skipped_rules))
    return field_values, rule_results
