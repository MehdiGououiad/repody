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
from repody.rules.values import field_key, literal, typed
from repody.schemas.rule import Condition, Operand, Rule, TableAggregate


def field(name: str) -> Operand:
    return Operand(kind="field", value=name)


def text(value: str) -> Operand:
    return Operand(kind="literal", value=value)


def cond(left: Operand, op: str = "==", right: Operand | None = None, **extra) -> Condition:
    return Condition(id="c", left=left, operator=op, right=right, **extra)  # type: ignore[arg-type]


def test_values_follow_the_declared_type():
    assert typed(6000, "number") == 6000
    assert typed("6 000,00", "number") is None  # text is not a number: never guessed
    assert typed(True, "number") is None
    assert typed("FAC-42", "verbatim-string") == "FAC-42"
    assert typed("", "string") is None
    assert typed([], "object-array") is None
    assert literal("6000", "number") == 6000.0
    assert literal(" true ", "boolean") is True
    assert literal("FAC-42", "string") == "FAC-42"
    with pytest.raises(ValueError):
        literal("six", "number")
    assert field_key("Total Amount") == "total_amount"
    assert field_key("Invoice.Total") == "invoice__total"


NUMBERS = {"ht": (5000, "number"), "tva": (1000, "number"), "ttc": (6000.0, "number")}
DATES = {"due": ("2024-02-01", "date"), "issued": ("2024-01-15", "date")}
TEXT = {"name": ("Acme", "string"), "label": ("Acme Corp", "string")}


@pytest.mark.parametrize(
    ("condition", "values", "expected"),
    [
        (cond(field("ttc"), "==", text("6000")), NUMBERS, True),
        (cond(field("ttc"), ">", text("6000")), NUMBERS, False),
        (
            cond(field("ht"), "==", field("ttc"), arithmetic_op="+", left_extra=field("tva")),
            NUMBERS,
            True,
        ),
        (
            cond(field("a"), "==", text("0.3"), arithmetic_op="+", left_extra=text("0.1")),
            {"a": (0.2, "number")},
            True,
        ),
        (cond(field("q"), "==", text("0.0001")), {"q": (0.0001, "number")}, True),
        (cond(field("q"), "==", text("0.0002")), {"q": (0.0001, "number")}, False),
        (cond(field("cur"), "IN", text("MAD, EUR")), {"cur": ("EUR", "currency")}, True),
        (cond(field("cur"), "NOT_IN", text("MAD, EUR")), {"cur": ("USD", "currency")}, True),
        (cond(field("name"), "IN", field("label")), TEXT, True),
        (cond(field("due"), ">", field("issued")), DATES, True),
        (cond(field("paid"), "==", text("true")), {"paid": (True, "boolean")}, True),
        (cond(field("po"), "EXISTS"), {"po": (None, "string")}, False),
        (cond(field("po"), "IS_EMPTY"), {"po": (None, "string")}, True),
        (cond(field("ttc"), "==", text("1")), {"ttc": (None, "number")}, None),
        (cond(field("ttc"), "==", text("6000")), {"ttc": ("6 000,00", "number")}, None),
    ],
)
def test_check(condition, values, expected):
    assert check(condition, values) is expected


def test_unknown_field_and_bad_literal():
    with pytest.raises(LookupError):
        check(cond(field("nope"), "==", text("1")), {})
    with pytest.raises(ValueError):
        check(cond(field("ttc"), "==", text("six")), NUMBERS)
    text_sum = cond(field("a"), "==", text("1"), arithmetic_op="+", left_extra=field("b"))
    with pytest.raises(TypeError, match="arithmetic needs number fields"):
        check(text_sum, {"a": ("5000", "verbatim-string"), "b": ("1000", "verbatim-string")})


def test_table_aggregates():
    rows = [
        {"label": "Card payment", "amount": -10.5},
        {"label": "Card refund", "amount": 4.5},
        {"label": "Transfer", "amount": 100},
        {"label": "Card fee", "amount": "n/a"},  # not a number: not summed
    ]
    values = {"lines": (rows, "object-array")}

    def agg(fn: str, **columns: str) -> Condition:
        aggregate = TableAggregate(fn=fn, table_field="lines", **columns)  # type: ignore[arg-type]
        return cond(field(""), "==", text("0"), table_aggregate=aggregate)

    total = agg("sum_rows", amount_column="amount")
    cards = agg(
        "sum_rows_where", amount_column="amount", filter_column="label", filter_contains="CARD"
    )
    count = agg("count_rows_where", filter_column="label", filter_contains="card")
    assert check(total.model_copy(update={"right": text("94")}), values)
    assert check(cards.model_copy(update={"right": text("-6")}), values)
    assert check(count.model_copy(update={"right": text("3")}), values)
    assert describe(count) == 'count_rows_where(lines, label, contains "card") == 0'


def test_rule_outcome_flags_only_failing_conditions():
    rule = Rule(
        id="r",
        name="Totals",
        conditions=[cond(field("ttc"), "==", text("6000")), cond(field("tva"), "<", text("500"))],
    )
    outcome = evaluate_rule(rule, NUMBERS)
    assert outcome.status == "failed"
    assert outcome.affected_fields == ["tva"]
    assert outcome.expression == "ttc == 6000 and tva < 500"
    assert "Not satisfied: tva < 500" in outcome.detail


def test_rule_skipped_when_value_missing():
    rule = Rule(id="r", conditions=[cond(field("ttc"), "==", text("1"))])
    assert evaluate_rule(rule, {"ttc": (None, "number")}).status == "skipped"
    assert evaluate_rule(rule, {}).status == "skipped"
    assert evaluate_rule(rule, {"ttc": (1, "number")}).status == "passed"


TYPES = {
    "ttc": "number",
    "name": "verbatim-string",
    "due": "date",
    "lines": "object-array",
}
LINES_COUNT = TableAggregate(fn="count_rows_where", table_field="ttc")


@pytest.mark.parametrize(
    ("condition", "issue"),
    [
        (cond(field(""), "==", text("1")), "Choose a field on the left."),
        (cond(field("ttc"), "=="), "Enter a value or field on the right."),
        (cond(field("ttc"), "EXISTS"), None),
        (cond(field("ttc"), ">", text("100")), None),
        (cond(field("due"), ">=", text("2024-01-01")), None),
        (
            cond(field("name"), ">", text("A")),
            "> compares numbers or dates; the left side is verbatim-string.",
        ),
        (cond(field("ttc"), "==", text("six")), "'six' is not a number value."),
        (
            cond(field("missing"), "==", text("1")),
            "Unknown field missing: it is not in the document schemas.",
        ),
        (
            cond(field("name"), "==", text("1"), arithmetic_op="+", left_extra=field("ttc")),
            "Arithmetic needs number fields; name is not a number.",
        ),
        (
            cond(field(""), "==", text("1"), table_aggregate=LINES_COUNT),
            "ttc is not an object-array field.",
        ),
    ],
)
def test_authoring_issues(condition, issue):
    assert condition_issue(condition, TYPES) == issue


def test_rule_issues_are_labelled():
    assert rule_issues(Rule(id="r", name="Empty")) == ["Empty: Add at least one condition."]
    incomplete = cond(field("ttc"), "==", text("1"), arithmetic_op="+")
    rule = Rule(id="r", name="Sum", conditions=[incomplete])
    assert rule_issues(rule) == ["Sum: Condition 1: Choose the second operand of the arithmetic."]


def test_cross_document_namespace():
    rows = [
        ("total", 6000, "Invoice", "number"),
        ("total", 6000, "Purchase Order", "number"),
        ("vendor", "Acme", "Invoice", "verbatim-string"),
    ]
    types = {"inv": "Invoice", "po": "Purchase Order"}
    cross = Rule(
        id="cross",
        scope="cross",
        applies_to=["inv", "po"],
        conditions=[cond(field("invoice.total"), "==", field("purchase order.total"))],
    )
    values = field_values(rows, rule=cross, doc_types_by_id=types, multi_document=True)
    assert values["invoice__total"] == (6000, "number")
    assert "total" not in values  # ambiguous across the two documents
    assert values["vendor"] == ("Acme", "verbatim-string")  # only one document has it
    [outcome] = evaluate_rules([cross], rows, doc_types_by_id=types, multi_document=True)
    assert outcome.status == "passed"
