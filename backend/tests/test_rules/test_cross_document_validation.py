"""Real-world cross-document (inter-doc) validation: field-to-field and field-to-value rules."""

from __future__ import annotations

import pytest

from audit_workbench.extraction.base import ExtractedFieldResult, ExtractionResult
from audit_workbench.rules.conditions import resolve_rule_body
from audit_workbench.rules.runner import evaluate_rules, validate_extractions
from audit_workbench.services.field_namespace import field_values_for_rule, field_values_from_extractions


def _field(key: str, value: str, *, extracted: bool = True) -> ExtractedFieldResult:
    return ExtractedFieldResult(
        key=key,
        description=key,
        value=value,
        type="string",
        confidence=0.95,
        extracted=extracted,
    )


def _result(fields: dict[str, str], *, extracted: bool = True) -> ExtractionResult:
    return ExtractionResult(
        fields=[_field(k, v, extracted=extracted) for k, v in fields.items()]
    )


DOC_INVOICE = "doc-invoice"
DOC_PO = "doc-po"
DOC_FACTURE_1 = "doc-f1"
DOC_FACTURE_2 = "doc-f2"

DOC_TYPES_INVOICE_PO = {DOC_INVOICE: "Invoice", DOC_PO: "Purchase Order"}
DOC_TYPES_FACTURES = {DOC_FACTURE_1: "Facture 1", DOC_FACTURE_2: "Facture 2"}


def _cross_rule(
    *,
    rule_id: str,
    body: str,
    applies_to: list[str],
    conditions: list[dict] | None = None,
) -> dict:
    rule: dict = {
        "id": rule_id,
        "name": "Cross check",
        "kind": "logic",
        "scope": "cross",
        "applies_to": applies_to,
        "body": body,
        "severity": "reject",
    }
    if conditions is not None:
        rule["conditions"] = conditions
    return rule


async def _eval_cross(
    rows: list[tuple[str, str, str | None]],
    rule: dict,
    *,
    doc_types: dict[str, str],
) -> str:
    field_values = field_values_from_extractions(rows, multi_document=True)
    results = await evaluate_rules(
        [rule],
        field_values,
        extraction_rows=rows,
        doc_types_by_id=doc_types,
        multi_document=True,
    )
    assert len(results) == 1
    return results[0].status


# --- Field namespace (cross-doc keys) ---


def test_cross_doc_prefixed_keys_for_invoice_and_po():
    rows = [
        ("po_number", "PO-2024-991", "Invoice"),
        ("total_amount", "6200.00", "Invoice"),
        ("po_number", "PO-2024-991", "Purchase Order"),
        ("approved_total", "6500.00", "Purchase Order"),
    ]
    values = field_values_from_extractions(rows, multi_document=True)
    assert values["invoice.po_number"] == "PO-2024-991"
    assert values["purchase_order.po_number"] == "PO-2024-991"
    assert values["invoice.total_amount"] == "6200.00"
    assert values["purchase_order.approved_total"] == "6500.00"


def test_cross_scope_limits_fields_to_applies_to_documents():
    rows = [
        ("po_number", "PO-111", "Invoice"),
        ("po_number", "PO-222", "Purchase Order"),
        ("po_number", "PO-999", "Delivery Note"),
    ]
    doc_types = {
        "d-inv": "Invoice",
        "d-po": "Purchase Order",
        "d-dn": "Delivery Note",
    }
    rule = _cross_rule(
        rule_id="r-scope",
        body="invoice__po_number == purchase_order__po_number",
        applies_to=["d-inv", "d-po"],
    )
    scoped = field_values_for_rule(
        rows,
        rule,
        doc_types_by_id=doc_types,
        multi_document=True,
    )
    assert "delivery_note.po_number" not in scoped
    assert scoped["invoice.po_number"] == "PO-111"
    assert scoped["purchase_order.po_number"] == "PO-222"


# --- Cross field == field (matching values) ---


@pytest.mark.asyncio
async def test_invoice_po_number_matches_po_document():
    rows = [
        ("po_number", "PO-2024-991", "Invoice"),
        ("po_number", "PO-2024-991", "Purchase Order"),
    ]
    rule = _cross_rule(
        rule_id="r-po-match",
        body="invoice__po_number == purchase_order__po_number",
        applies_to=[DOC_INVOICE, DOC_PO],
    )
    status = await _eval_cross(rows, rule, doc_types=DOC_TYPES_INVOICE_PO)
    assert status == "passed"


@pytest.mark.asyncio
async def test_invoice_po_number_mismatch_fails():
    rows = [
        ("po_number", "PO-2024-991", "Invoice"),
        ("po_number", "PO-2024-992", "Purchase Order"),
    ]
    rule = _cross_rule(
        rule_id="r-po-mismatch",
        body="invoice__po_number == purchase_order__po_number",
        applies_to=[DOC_INVOICE, DOC_PO],
    )
    status = await _eval_cross(rows, rule, doc_types=DOC_TYPES_INVOICE_PO)
    assert status == "failed"


@pytest.mark.asyncio
async def test_two_facture_totals_match_with_ui_tokens():
    """Mirrors benchmark_ui_route logic-cross scenario."""
    rows = [
        ("total_amount", "6000.00", "Facture 1"),
        ("total_amount", "6000.00", "Facture 2"),
    ]
    rule = _cross_rule(
        rule_id="r-totals",
        body="facture_1__total_amount == facture_2__total_amount",
        applies_to=[DOC_FACTURE_1, DOC_FACTURE_2],
    )
    status = await _eval_cross(rows, rule, doc_types=DOC_TYPES_FACTURES)
    assert status == "passed"


@pytest.mark.asyncio
async def test_two_facture_totals_mismatch_fails():
    rows = [
        ("total_amount", "6000.00", "Facture 1"),
        ("total_amount", "6200.00", "Facture 2"),
    ]
    rule = _cross_rule(
        rule_id="r-totals-bad",
        body="facture_1__total_amount == facture_2__total_amount",
        applies_to=[DOC_FACTURE_1, DOC_FACTURE_2],
    )
    status = await _eval_cross(rows, rule, doc_types=DOC_TYPES_FACTURES)
    assert status == "failed"


@pytest.mark.asyncio
async def test_cross_field_match_with_dotted_tokens():
    rows = [
        ("vendor_name", "Acme Corp Ltd.", "Invoice"),
        ("vendor_name", "Acme Corp Ltd.", "Purchase Order"),
    ]
    rule = _cross_rule(
        rule_id="r-vendor",
        body="invoice__vendor_name == purchase_order__vendor_name",
        applies_to=[DOC_INVOICE, DOC_PO],
    )
    status = await _eval_cross(rows, rule, doc_types=DOC_TYPES_INVOICE_PO)
    assert status == "passed"


# --- Cross field vs field with numeric coercion (locale formats) ---


@pytest.mark.asyncio
async def test_cross_numeric_match_across_locale_formats():
    rows = [
        ("total_amount", "6 000,00 Dh TTC", "Facture 1"),
        ("total_amount", "6000.00", "Facture 2"),
    ]
    rule = _cross_rule(
        rule_id="r-locale",
        body="facture_1__total_amount == facture_2__total_amount",
        applies_to=[DOC_FACTURE_1, DOC_FACTURE_2],
    )
    status = await _eval_cross(rows, rule, doc_types=DOC_TYPES_FACTURES)
    assert status == "passed"


@pytest.mark.asyncio
async def test_invoice_total_within_po_approved_limit():
    """Invoice total must not exceed PO approved amount."""
    rows = [
        ("total_amount", "6200.00", "Invoice"),
        ("approved_total", "6500.00", "Purchase Order"),
    ]
    rule = _cross_rule(
        rule_id="r-limit",
        body="invoice__total_amount <= purchase_order__approved_total",
        applies_to=[DOC_INVOICE, DOC_PO],
    )
    status = await _eval_cross(rows, rule, doc_types=DOC_TYPES_INVOICE_PO)
    assert status == "passed"


@pytest.mark.asyncio
async def test_invoice_total_exceeds_po_approved_limit_fails():
    rows = [
        ("total_amount", "7200.00", "Invoice"),
        ("approved_total", "6500.00", "Purchase Order"),
    ]
    rule = _cross_rule(
        rule_id="r-limit-bad",
        body="invoice__total_amount <= purchase_order__approved_total",
        applies_to=[DOC_INVOICE, DOC_PO],
    )
    status = await _eval_cross(rows, rule, doc_types=DOC_TYPES_INVOICE_PO)
    assert status == "failed"


# --- Cross field vs literal value (champ vs valeur) ---


@pytest.mark.asyncio
async def test_cross_field_equals_literal_value_passes():
    rows = [
        ("currency", "EUR", "Invoice"),
        ("currency", "MAD", "Purchase Order"),
    ]
    rule = _cross_rule(
        rule_id="r-currency",
        body='invoice__currency == "EUR"',
        applies_to=[DOC_INVOICE, DOC_PO],
    )
    status = await _eval_cross(rows, rule, doc_types=DOC_TYPES_INVOICE_PO)
    assert status == "passed"


@pytest.mark.asyncio
async def test_cross_field_equals_literal_value_fails():
    rows = [
        ("currency", "MAD", "Invoice"),
        ("currency", "MAD", "Purchase Order"),
    ]
    rule = _cross_rule(
        rule_id="r-currency-bad",
        body='invoice__currency == "EUR"',
        applies_to=[DOC_INVOICE, DOC_PO],
    )
    status = await _eval_cross(rows, rule, doc_types=DOC_TYPES_INVOICE_PO)
    assert status == "failed"


# --- UI condition builder → cross expression ---


@pytest.mark.asyncio
async def test_cross_rule_from_visual_conditions():
    """UI stores facture.total_amount vs facture_2.total_amount in conditions."""
    rows = [
        ("total_amount", "789.00", "FACTURE"),
        ("total_amount", "789.00", "FACTURE 2"),
    ]
    doc_types = {"d-a": "FACTURE", "d-b": "FACTURE 2"}
    rule = _cross_rule(
        rule_id="r-cond",
        body="",
        applies_to=["d-a", "d-b"],
        conditions=[
            {
                "id": "c1",
                "left": {"kind": "field", "value": "facture.total_amount"},
                "operator": "==",
                "right": {"kind": "field", "value": "facture_2.total_amount"},
            }
        ],
    )
    compiled = resolve_rule_body(rule)
    assert compiled == "facture__total_amount == facture_2__total_amount"
    rule["body"] = compiled
    status = await _eval_cross(rows, rule, doc_types=doc_types)
    assert status == "passed"


# --- Missing / empty values ---


@pytest.mark.asyncio
async def test_cross_rule_skipped_when_one_field_missing():
    rows = [
        ("po_number", "PO-2024-991", "Invoice"),
        ("po_number", "—", "Purchase Order"),
    ]
    rule = _cross_rule(
        rule_id="r-missing",
        body="invoice__po_number == purchase_order__po_number",
        applies_to=[DOC_INVOICE, DOC_PO],
    )
    status = await _eval_cross(rows, rule, doc_types=DOC_TYPES_INVOICE_PO)
    assert status == "skipped"


@pytest.mark.asyncio
async def test_cross_rule_skipped_when_field_not_in_schema():
    rows = [
        ("po_number", "PO-2024-991", "Invoice"),
        ("approved_total", "6500.00", "Purchase Order"),
    ]
    rule = _cross_rule(
        rule_id="r-unknown",
        body="invoice__po_number == purchase_order__reference_id",
        applies_to=[DOC_INVOICE, DOC_PO],
    )
    status = await _eval_cross(rows, rule, doc_types=DOC_TYPES_INVOICE_PO)
    assert status == "skipped"


# --- End-to-end validate_extractions ---


@pytest.mark.asyncio
async def test_validate_extractions_multi_document_cross_rules():
    extractions = [
        (
            "Invoice",
            _result({"po_number": "PO-2024-991", "total_amount": "6200.00"}),
        ),
        (
            "Purchase Order",
            _result({"po_number": "PO-2024-991", "approved_total": "6500.00"}),
        ),
    ]
    rules = [
        _cross_rule(
            rule_id="r-po",
            body="invoice__po_number == purchase_order__po_number",
            applies_to=[DOC_INVOICE, DOC_PO],
        ),
        _cross_rule(
            rule_id="r-cap",
            body="invoice__total_amount <= purchase_order__approved_total",
            applies_to=[DOC_INVOICE, DOC_PO],
        ),
    ]
    doc_types = {DOC_INVOICE: "Invoice", DOC_PO: "Purchase Order"}
    _values, results = await validate_extractions(
        extractions=extractions,
        rules=rules,
        multi_document=True,
        doc_types_by_id=doc_types,
    )
    by_id = {row.id: row.status for row in results}
    assert by_id["r-po"] == "passed"
    assert by_id["r-cap"] == "passed"


@pytest.mark.asyncio
async def test_validate_extractions_flags_math_and_cross_failures():
    """Realistic audit: invoice math wrong AND PO mismatch."""
    extractions = [
        (
            "Invoice",
            _result(
                {
                    "subtotal": "5625.00",
                    "tax": "478.13",
                    "total_amount": "6200.00",
                    "po_number": "PO-WRONG",
                }
            ),
        ),
        ("Purchase Order", _result({"po_number": "PO-2024-991", "approved_total": "6000.00"})),
    ]
    rules = [
        {
            "id": "r-math",
            "name": "Math integrity",
            "kind": "logic",
            "scope": "intra",
            "applies_to": [DOC_INVOICE],
            "body": "subtotal + tax == total_amount",
            "severity": "reject",
        },
        _cross_rule(
            rule_id="r-po",
            body="invoice__po_number == purchase_order__po_number",
            applies_to=[DOC_INVOICE, DOC_PO],
        ),
        _cross_rule(
            rule_id="r-cap",
            body="invoice__total_amount <= purchase_order__approved_total",
            applies_to=[DOC_INVOICE, DOC_PO],
        ),
    ]
    doc_types = {DOC_INVOICE: "Invoice", DOC_PO: "Purchase Order"}
    _values, results = await validate_extractions(
        extractions=extractions,
        rules=rules,
        multi_document=True,
        doc_types_by_id=doc_types,
    )
    by_id = {row.id: row.status for row in results}
    assert by_id["r-math"] == "failed"
    assert by_id["r-po"] == "failed"
    assert by_id["r-cap"] == "failed"
