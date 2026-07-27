from audit_workbench.rules.rule_syntax import validate_logic_rule_body


def test_validate_date_comparison_expression():
    assert validate_logic_rule_body('invoice_date < "2025-01-01"') is None
    assert validate_logic_rule_body('due_date <= "2025-12-31"') is None
    assert validate_logic_rule_body("total_amount > 1000") is None
