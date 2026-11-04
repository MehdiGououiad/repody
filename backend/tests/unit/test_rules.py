import json

import pytest

from repody.rules.evaluate import (
    check,
    condition_issue,
    describe,
    evaluate_rule,
    evaluate_rules,
    field_values,
    rule_issues,
)
from repody.rules.models import Condition, Operand, Rule, TableAggregate
from repody.rules.values import MISSING, coerce, field_key, normalize_amount, parse_numeric_value


def field(name: str) -> Operand:
    return Operand(kind="field", value=name)


def literal(value: str) -> Operand:
    return Operand(kind="literal", value=value)


def cond(left: Operand, op: str = "==", right: Operand | None = None, **extra) -> Condition:
    return Condition(id="c", left=left, operator=op, right=right, **extra)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("text", "amount"),
    [
        ("6 000,00 Dh", 6000.0),
        ("1.234,56", 1234.56),
        ("1,234.56", 1234.56),
        ("-50.00 MAD", -50.0),
        ("−12", -12.0),
        ("29 944,40", 29944.4),
        ("PO-2024-991", None),
        ("2024-01-15", None),
        (MISSING, None),
    ],
)
def test_amounts(text, amount):
    assert parse_numeric_value(text) == amount


def test_coerce_and_keys():
    assert coerce("2024-01-15") == "2024-01-15"
    assert coerce("true") is True
    assert coerce(MISSING) is None
    assert coerce("FAC-42") == "FAC-42"
    assert normalize_amount("6 000,00") == "6000.00"
    assert field_key("Total Amount") == "total_amount"
    assert field_key("Invoice.Total") == "invoice__total"


@pytest.mark.parametrize(
    ("condition", "values", "expected"),
    [
        (cond(field("total"), "==", literal("6000")), {"total": "6 000,00"}, True),
        (cond(field("total"), ">", literal("6000")), {"total": "6000"}, False),
        (
            cond(field("ht"), "==", field("ttc"), arithmetic_op="+", left_extra=field("tva")),
            {"ht": "5000", "tva": "1000", "ttc": "6000.00"},
            True,
        ),
        (
            cond(field("a"), "==", literal("0.3"), arithmetic_op="+", left_extra=literal("0.1")),
            {"a": "0.2"},
            True,
        ),
        (cond(field("currency"), "IN", literal("MAD, EUR")), {"currency": "EUR"}, True),
        (cond(field("currency"), "NOT_IN", literal("MAD, EUR")), {"currency": "USD"}, True),
        (cond(field("name"), "IN", field("label")), {"name": "Acme", "label": "Acme Corp"}, True),
        (
            cond(field("due"), ">", field("issued")),
            {"due": "2024-02-01", "issued": "2024-01-15"},
            True,
        ),
        (cond(field("po"), "EXISTS"), {"po": MISSING}, False),
        (cond(field("po"), "IS_EMPTY"), {"po": MISSING}, True),
        (cond(field("total"), "==", literal("1")), {"total": MISSING}, None),
    ],
)
def test_check(condition, values, expected):
    assert check(condition, values) is expected


def test_unknown_field_raises():
    with pytest.raises(LookupError):
        check(cond(field("nope"), "==", literal("1")), {})


def test_table_aggregates():
    table = json.dumps(
        [
            {"Label": "Card payment", "Amount": "-10.50"},
            {"Label": "Card refund", "Amount": "4.50"},
            {"Label": "Transfer", "Amount": "100"},
        ]
    )
    values = {"lines": table}
    total = TableAggregate(fn="sum_rows", table_field="lines", amount_column="amount")
    cards = TableAggregate(
        fn="sum_rows_where",
        table_field="lines",
        amount_column="amount",
        filter_column="label",
        filter_contains="card",
    )
    count = TableAggregate(
        fn="count_rows_where", table_field="lines", filter_column="label", filter_contains="card"
    )
    assert check(cond(field(""), "==", literal("94"), table_aggregate=total), values)
    assert check(cond(field(""), "==", literal("-6"), table_aggregate=cards), values)
    assert check(cond(field(""), "==", literal("2"), table_aggregate=count), values)
    assert describe(cond(field(""), "==", literal("2"), table_aggregate=count)) == (
        'count_rows_where(lines, label, contains "card") == 2'
    )


def test_rule_outcome_flags_only_failing_conditions():
    rule = Rule(
        id="r",
        name="Totals",
        conditions=[
            cond(field("total"), "==", literal("6000")),
            cond(field("tva"), "<", literal("500")),
        ],
    )
    outcome = evaluate_rule(rule, {"total": "6000", "tva": "1000"})
    assert outcome.status == "failed"
    assert outcome.affected_fields == ["tva"]
    assert outcome.expression == "total == 6000 and tva < 500"
    assert "Not satisfied: tva < 500" in outcome.detail


def test_rule_skipped_when_value_missing():
    rule = Rule(id="r", conditions=[cond(field("total"), "==", literal("1"))])
    assert evaluate_rule(rule, {"total": MISSING}).status == "skipped"
    assert evaluate_rule(rule, {}).status == "skipped"
    assert evaluate_rule(rule, {"total": "1"}).status == "passed"


def test_type_mismatch_fails_the_rule():
    rule = Rule(id="r", conditions=[cond(field("name"), ">", literal("5"))])
    outcome = evaluate_rule(rule, {"name": "Acme"})
    assert outcome.status == "failed"
    assert "Cannot evaluate" in outcome.detail


def test_authoring_issues():
    assert rule_issues(Rule(id="r", name="Empty")) == ["Empty: Add at least one condition."]
    assert condition_issue(cond(field(""), "==", literal("1"))) == "Choose a field on the left."
    assert condition_issue(cond(field("a"), "==")) == "Enter a value or field on the right."
    assert condition_issue(cond(field("a"), "EXISTS")) is None
    incomplete = Rule(
        id="r", name="Sum", conditions=[cond(field("a"), "==", literal("1"), arithmetic_op="+")]
    )
    assert rule_issues(incomplete) == [
        "Sum: Condition 1: Choose the second operand of the arithmetic."
    ]


async def test_cross_document_namespace():
    rows = [
        ("total", "6000", "Invoice"),
        ("total", "6000", "Purchase Order"),
        ("vendor", "Acme", "Invoice"),
    ]
    types = {"inv": "Invoice", "po": "Purchase Order"}
    cross = Rule(
        id="cross",
        scope="cross",
        applies_to=["inv", "po"],
        conditions=[cond(field("invoice.total"), "==", field("purchase order.total"))],
    )
    values = field_values(rows, rule=cross, doc_types_by_id=types, multi_document=True)
    assert values["invoice__total"] == "6000"
    assert "total" not in values  # ambiguous across the two documents
    assert values["vendor"] == "Acme"  # only one document has it
    [outcome] = await evaluate_rules([cross], rows, doc_types_by_id=types, multi_document=True)
    assert outcome.status == "passed"
