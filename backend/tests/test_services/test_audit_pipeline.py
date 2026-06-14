from audit_workbench.services.audit_pipeline import field_values_from_extractions


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
