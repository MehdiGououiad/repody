from audit_workbench.rules.conditions import resolve_rule_body


def test_resolve_rule_body_from_conditions():
    rule = {
        "body": "",
        "condition_junction": "AND",
        "conditions": [
            {
                "id": "c1",
                "left": {"kind": "field", "value": "tva"},
                "operator": "<",
                "right": {"kind": "literal", "value": "500"},
            }
        ],
    }
    assert resolve_rule_body(rule) == "tva < 500.0"


def test_resolve_rule_body_arithmetic():
    rule = {
        "body": "",
        "conditions": [
            {
                "id": "c1",
                "left": {"kind": "field", "value": "subtotal"},
                "arithmeticOp": "+",
                "leftExtra": {"kind": "field", "value": "tax"},
                "operator": "==",
                "right": {"kind": "field", "value": "total_amount"},
            }
        ],
    }
    expr = resolve_rule_body(rule)
    assert "subtotal" in expr and "tax" in expr and "total_amount" in expr


def test_resolve_rule_body_uses_stored_compiled_expression():
    rule = {"body": "total_amount == 6000", "conditions": []}
    assert resolve_rule_body(rule) == "total_amount == 6000"


def test_llm_rule_uses_body():
    rule = {"kind": "llm", "body": "Verify totals.", "conditions": []}
    assert resolve_rule_body(rule) == "Verify totals."


def test_resolve_rule_body_spaced_field_names():
    """UI schema labels like 'tva total' must compile to tva_total."""
    rule = {
        "body": "",
        "conditions": [
            {
                "id": "c1",
                "left": {"kind": "field", "value": "tva total"},
                "operator": "<",
                "right": {"kind": "literal", "value": "500"},
            }
        ],
    }
    assert resolve_rule_body(rule) == "tva_total < 500.0"


def test_resolve_rule_body_normalizes_dotted_cross_doc_tokens():
    rule = {
        "body": "",
        "conditions": [
            {
                "id": "c1",
                "left": {"kind": "field", "value": "Invoice.po_number"},
                "operator": "==",
                "right": {"kind": "field", "value": "Purchase Order.po_number"},
            }
        ],
    }
    assert resolve_rule_body(rule) == "invoice__po_number == purchase_order__po_number"


def test_resolve_rule_body_multiple_conditions_uses_python_and():
    rule = {
        "body": "(tva < 500 ) AND ( total_amount > 1000 )",
        "condition_junction": "AND",
        "conditions": [
            {
                "id": "c1",
                "left": {"kind": "field", "value": "tva"},
                "operator": "<",
                "right": {"kind": "literal", "value": "500"},
            },
            {
                "id": "c2",
                "left": {"kind": "field", "value": "total_amount"},
                "operator": ">",
                "right": {"kind": "literal", "value": "1000"},
            },
        ],
    }
    expr = resolve_rule_body(rule)
    assert expr == "(tva < 500.0) and (total_amount > 1000.0)"


def test_logic_check_entries_one_per_condition():
    from audit_workbench.rules.conditions import logic_check_entries

    rule = {
        "id": "r1",
        "name": "Invoice",
        "conditions": [
            {
                "id": "c0",
                "left": {"kind": "field", "value": "montant_total"},
                "operator": ">",
                "right": {"kind": "literal", "value": "1000"},
            },
            {
                "id": "c1",
                "left": {"kind": "field", "value": "tva_total"},
                "operator": "<",
                "right": {"kind": "literal", "value": "500"},
            },
        ],
    }
    checks = logic_check_entries(rule)
    assert len(checks) == 2
    assert checks[0]["body"] == "montant_total > 1000.0"
    assert checks[1]["body"] == "tva_total < 500.0"
    assert checks[0]["id"] == "r1-cc0"
    assert checks[1]["id"] == "r1-cc1"


def test_conditions_to_expression_or_junction():
    from audit_workbench.rules.conditions import conditions_to_expression

    expr = conditions_to_expression(
        [
            {
                "left": {"kind": "field", "value": "a"},
                "operator": "==",
                "right": {"kind": "literal", "value": "1"},
            },
            {
                "left": {"kind": "field", "value": "b"},
                "operator": "==",
                "right": {"kind": "literal", "value": "2"},
            },
        ],
        "OR",
    )
    assert expr == "(a == 1.0) or (b == 2.0)"
