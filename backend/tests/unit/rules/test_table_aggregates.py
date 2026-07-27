from audit_workbench.rules.conditions import resolve_rule_body
from audit_workbench.rules.logic_evaluator import evaluate_logic_expression
from audit_workbench.rules.table_aggregates import count_rows_where, sum_rows, sum_rows_where

ROWS = '[{"category": "type-a", "amount": "10.00"}, {"category": "type-b", "amount": "20.00"}, {"category": "type-a", "amount": "5.50"}]'


def test_sum_rows_where_filters_and_sums():
    assert sum_rows_where(ROWS, "amount", "category", "type-a") == 15.5


def test_sum_rows_all_rows():
    assert sum_rows(ROWS, "amount") == 35.5


def test_count_rows_where():
    assert count_rows_where(ROWS, "category", "type-a") == 2


def test_logic_rule_sum_rows_where_equals_literal():
    fields = {"line_items": ROWS}
    expr = 'sum_rows_where(line_items, "amount", "category", "type-a") == 15.5'
    passed, _, _ = evaluate_logic_expression(expr, fields)
    assert passed is True


def test_condition_builder_compiles_table_aggregate():
    rule = {
        "conditions": [
            {
                "id": "c1",
                "tableAggregate": {
                    "fn": "sum_rows_where",
                    "tableField": "line_items",
                    "amountColumn": "amount",
                    "filterColumn": "category",
                    "filterContains": "type-a",
                },
                "left": {"kind": "field", "value": ""},
                "operator": "==",
                "right": {"kind": "literal", "value": "15.5"},
            }
        ],
    }
    body = resolve_rule_body(rule)
    assert body == 'sum_rows_where(line_items, "amount", "category", "type-a") == 15.5'
