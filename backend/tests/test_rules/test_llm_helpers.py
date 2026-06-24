from __future__ import annotations

from audit_workbench.rules.llm_fields import (
    evaluate_fee_keyword_rule,
    referenced_fields,
    rule_field_values,
    unknown_reference_detail,
)
from audit_workbench.rules.llm_prompts import batch_rules_prompt, fields_block, single_rule_prompt


def test_rule_field_values_selects_referenced_fields_case_insensitively() -> None:
    selected, missing = rule_field_values(
        "Compare @Invoice.Total with @vendor.",
        {"invoice.total": "42", "vendor": "Acme", "ignored": "x"},
    )

    assert selected == {"Invoice.Total": "42", "vendor": "Acme"}
    assert missing == []


def test_rule_field_values_reports_unknown_references() -> None:
    selected, missing = rule_field_values("Check @missing_total.", {"total": "42"})

    assert selected == {}
    assert missing == ["missing_total"]
    assert unknown_reference_detail(missing) == "Unknown field reference(s): @missing_total."


def test_fee_keyword_rule_short_circuits_on_extracted_values() -> None:
    assert evaluate_fee_keyword_rule(
        "No late fee should appear.",
        {"terms": "Includes penalty after 30 days"},
    ) == ("failed", "Possible late-fee or penalty wording found in extracted field values.")
    assert evaluate_fee_keyword_rule("No late fee should appear.", {"terms": "Net 30"}) == (
        "passed",
        "No late-fee or penalty keywords found in extracted values.",
    )
    assert evaluate_fee_keyword_rule("Check total", {"terms": "penalty"}) is None


def test_prompt_helpers_filter_empty_values_and_preserve_rule_ids() -> None:
    assert referenced_fields("@total and @total and @invoice.tax") == [
        "total",
        "invoice.tax",
    ]
    assert fields_block({"total": "42", "empty": "", "dash": "\u2014"}) == "total=42"

    single = single_rule_prompt(
        rule_name="Total check",
        body="Verify @total.",
        field_values={"total": "42"},
    )
    assert 'Audit rule "Total check": Verify @total.' in single
    assert "total=42" in single

    batch = batch_rules_prompt(
        rules=[{"id": "r1", "name": "Rule one", "body": "Verify @total."}],
        field_values={"total": "42"},
    )
    assert 'id="r1"' in batch
    assert "Rule one" in batch
