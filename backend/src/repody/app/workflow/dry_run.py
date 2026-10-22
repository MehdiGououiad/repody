"""Dry run: evaluate a draft workflow's rules against sample field values (no model call)."""

from __future__ import annotations

from repody.extraction.pipeline import extract_document_fields
from repody.rules.conditions import resolve_rule_body
from repody.rules.runner import evaluate_dry_run_rules
from repody.schemas.workflow import (
    DryRunBody,
    DryRunExtracted,
    DryRunResponse,
    DryRunRuleResult,
)


async def dry_run_workflow(body: DryRunBody) -> DryRunResponse:
    rules = []
    for rule in body.rules_full or body.rules:
        row = rule.model_dump(by_alias=False)
        rules.append({**row, "body": resolve_rule_body(row)})

    named_fields = [f for f in body.fields if f.name.strip()]
    schema = [{"name": f.name, "description": f.description} for f in named_fields]
    sample_values = {
        f.name: f.sample_value
        for f in named_fields
        if f.sample_value is not None and f.sample_value.strip()
    }
    dry_fields = extract_document_fields(schema, sample_values=sample_values or None)
    field_values = {row.key: row.value for row in dry_fields if row.key.strip()}

    return DryRunResponse(
        extracted=[
            DryRunExtracted(field=row.key, value=row.value, matched=row.extracted)
            for row in dry_fields
        ],
        rule_results=[
            DryRunRuleResult.model_validate(row)
            for row in await evaluate_dry_run_rules(rules, field_values)
        ],
    )
