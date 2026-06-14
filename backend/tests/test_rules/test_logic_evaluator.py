from audit_workbench.rules.logic_evaluator import evaluate_logic_expression


def test_math_integrity_fails():
    fields = {
        "subtotal": "5625.00",
        "tax": "478.13",
        "total_amount": "6200.00",
    }
    passed, detail, _ = evaluate_logic_expression(
        "subtotal + tax == total_amount",
        fields,
    )
    assert passed is False
    assert "false" in detail.lower()


def test_positive_total_passes():
    fields = {"total_amount": "100.00"}
    passed, _, _ = evaluate_logic_expression("total_amount > 0", fields)
    assert passed is True


def test_missing_field_is_skipped_not_error():
    passed, detail, affected = evaluate_logic_expression("montant_total > 2000", {})
    assert passed is None
    assert "No value yet" in detail or "not found" in detail
    assert "montant_total" in affected


def test_empty_field_value_is_skipped():
    passed, detail, _ = evaluate_logic_expression("montant_total > 2000", {"montant total": "—"})
    assert passed is None
    assert "No value yet" in detail


def test_currency_suffix_coerces_for_comparison():
    fields = {"total_amount": "6000.00DhTTC"}
    passed, detail, _ = evaluate_logic_expression("total_amount < 1000", fields)
    assert passed is False
    assert "false" in detail.lower()


def test_ocr_locale_amount_coerces():
    fields = {"total_amount": "6 000,00 Dh TTC"}
    passed, _, _ = evaluate_logic_expression("total_amount > 1000", fields)
    assert passed is True
