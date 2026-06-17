from audit_workbench.services.field_namespace import (
    field_values_for_rule,
    field_values_from_extractions,
)


def test_multi_doc_prefixed_field_keys():
    rows = [
        ("total_amount", "100.00", "Invoice"),
        ("total_amount", "200.00", "Purchase Order"),
    ]
    values = field_values_from_extractions(rows, multi_document=True)
    assert values["invoice.total_amount"] == "100.00"
    assert values["purchase_order.total_amount"] == "200.00"


def test_single_doc_bare_keys_only():
    rows = [("total_amount", "6000.00", "Invoice")]
    values = field_values_from_extractions(rows, multi_document=False)
    assert values["total_amount"] == "6000.00"


def test_intra_rule_scoped_to_one_doc_in_multi_doc_workflow():
    """Bare keys must resolve when the same field name exists on multiple documents."""
    rows = [
        ("TOTAL", "789.00", "FACTURE"),
        ("TOTAL", "6000.00", "FACTURE 2"),
    ]
    doc_types = {"doc-a": "FACTURE", "doc-b": "FACTURE 2"}
    rule = {
        "id": "r1",
        "scope": "intra",
        "applies_to": ["doc-a"],
        "body": "total > 6000.0",
    }
    values = field_values_for_rule(
        rows,
        rule,
        doc_types_by_id=doc_types,
        multi_document=True,
    )
    assert values["total"] == "789.00"
    assert values["TOTAL"] == "789.00"
    assert values["facture.total"] == "789.00"
    assert values["facture.TOTAL"] == "789.00"


async def test_intra_rule_evaluates_with_scoped_fields():
    from audit_workbench.rules.runner import evaluate_rules

    rows = [
        ("TOTAL", "789.00", "FACTURE"),
        ("TOTAL", "6000.00", "FACTURE 2"),
    ]
    doc_types = {"doc67175974": "FACTURE", "doc-other": "FACTURE 2"}
    rules = [
        {
            "id": "r315b68a2",
            "name": "Total check",
            "scope": "intra",
            "applies_to": ["doc67175974"],
            "kind": "logic",
            "body": "total > 6000",
            "severity": "reject",
        }
    ]
    field_values = field_values_from_extractions(rows, multi_document=True)
    results = await evaluate_rules(
        rules,
        field_values,
        extraction_rows=rows,
        doc_types_by_id=doc_types,
        multi_document=True,
    )
    assert len(results) == 1
    assert results[0].status != "skipped"
    assert "not found" not in (results[0].detail or "").lower()


async def test_intra_rule_with_ui_prefixed_token_on_single_doc():
    """UI emits facture1__total for multi-doc workflows even on intra rules."""
    from audit_workbench.rules.runner import evaluate_rules

    rows = [
        ("total", "789.00", "facture1"),
        ("total", "6000.00", "facture2"),
    ]
    doc_types = {"doc-a": "facture1", "doc-b": "facture2"}
    rules = [
        {
            "id": "r1",
            "name": "Facture1 total",
            "scope": "intra",
            "applies_to": ["doc-a"],
            "kind": "logic",
            "body": "facture1__total > 6000.0",
            "severity": "reject",
        }
    ]
    field_values = field_values_from_extractions(rows, multi_document=True)
    results = await evaluate_rules(
        rules,
        field_values,
        extraction_rows=rows,
        doc_types_by_id=doc_types,
        multi_document=True,
    )
    assert len(results) == 1
    assert results[0].status == "failed"
    assert "not found" not in (results[0].detail or "").lower()
