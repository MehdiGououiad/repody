import pytest

from repody.rules.evaluate import (
    SchemaTypes,
    check,
    condition_issue,
    describe,
    evaluate_rule,
    evaluate_rules,
    field_values,
    rule_issues,
)
from repody.rules.tables import sum_rows
from repody.rules.values import field_key, literal, typed
from repody.schemas.rule import (
    Aggregate,
    Arithmetic,
    Condition,
    Expression,
    FieldRef,
    LiteralValue,
    Operand,
    Rule,
)


def field(name: str) -> FieldRef:
    return FieldRef(field=name)


def text(value: str) -> LiteralValue:
    return LiteralValue(value=value)


def plus(a: str, b: str) -> Arithmetic:
    return Arithmetic(op="+", left=field(a), right=field(b))


def cond(left: Expression, op: str = "==", right: Operand | None = None) -> Condition:
    return Condition(id="c", left=left, operator=op, right=right)  # type: ignore[arg-type]


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
    with pytest.raises(ValueError, match="could not convert"):
        literal("six", "number")
    assert field_key("Total  Amount") == "total_amount"
    assert field_key("Invoice.Total") == "invoice__total"


NUMBERS = {"ht": (5000, "number"), "tva": (1000, "number"), "ttc": (6000.0, "number")}
DATES = {"due": ("2024-02-01", "date"), "issued": ("2024-01-15", "date")}
TEXT = {"name": ("Acme", "string"), "label": ("Acme Corp", "string")}


@pytest.mark.parametrize(
    ("condition", "values", "expected"),
    [
        (cond(field("ttc"), "==", text("6000")), NUMBERS, True),
        (cond(field("ttc"), ">", text("6000")), NUMBERS, False),
        (cond(plus("ht", "tva"), "==", field("ttc")), NUMBERS, True),
        (
            cond(plus("a", "b"), "==", text("0.3")),
            {"a": (0.2, "number"), "b": (0.1, "number")},
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
        (cond(plus("ht", "x"), "==", text("1")), {**NUMBERS, "x": (None, "number")}, None),
    ],
)
def test_check(condition, values, expected):
    assert check(condition, values) is expected


def test_unknown_field_and_bad_literal():
    with pytest.raises(LookupError):
        check(cond(field("nope"), "==", text("1")), {})
    with pytest.raises(ValueError, match="could not convert"):
        check(cond(field("ttc"), "==", text("six")), NUMBERS)
    with pytest.raises(TypeError, match="arithmetic needs number fields"):
        check(
            cond(plus("a", "b"), "==", text("1")),
            {"a": ("5000", "verbatim-string"), "b": ("1000", "verbatim-string")},
        )


ROWS = [
    {"Label": "Card payment", "Unit Price": -10.5},
    {"Label": "Card refund", "Unit Price": 4.5},
    {"Label": "Transfer", "Unit Price": 100},
    {"Label": "Card fee", "Unit Price": "n/a"},  # not a number: not summed
]


def test_table_aggregates_read_columns_by_their_schema_name():
    values = {"lines": (ROWS, "object-array")}
    total = Aggregate(fn="sum_rows", table="lines", column="Unit Price")
    cards = Aggregate(
        fn="sum_rows_where",
        table="lines",
        column="Unit Price",
        filter_column="Label",
        filter_contains="CARD",
    )
    count = Aggregate(
        fn="count_rows_where", table="lines", filter_column="Label", filter_contains="card"
    )
    assert check(cond(total, "==", text("94")), values)
    assert check(cond(cards, "==", text("-6")), values)
    assert check(cond(count, "==", text("3")), values)
    assert (
        describe(cond(count, "==", text("0")))
        == 'count_rows_where(lines, Label, contains "card") == 0'
    )


def test_a_column_spelled_differently_by_the_model_still_matches():
    assert sum_rows([{"unit_price": 2}, {"UNIT PRICE": 3}], "Unit Price") == 5


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


SCHEMA = SchemaTypes(
    fields={"ttc": "number", "name": "verbatim-string", "due": "date", "lines": "object-array"},
    columns={"lines": {"label": "verbatim-string", "unit_price": "number"}},
)


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
            cond(plus("name", "ttc"), "==", text("1")),
            "Arithmetic needs number fields; name is not a number.",
        ),
        (
            cond(Aggregate(fn="count_rows_where", table="ttc"), "==", text("1")),
            "ttc is not an object-array field.",
        ),
        (
            cond(Aggregate(table="lines", column="Unit Price"), ">", text("0")),
            None,
        ),
        (
            cond(Aggregate(table="lines", column="Label"), ">", text("0")),
            "Sums need a number column; Label is verbatim-string.",
        ),
        (
            cond(Aggregate(table="lines", column="Price"), ">", text("0")),
            "Unknown column Price in lines.",
        ),
        (cond(Aggregate(table="lines"), ">", text("0")), "Choose the column to sum."),
    ],
)
def test_authoring_issues(condition, issue):
    assert condition_issue(condition, SCHEMA) == issue


def test_rule_issues_are_labelled():
    assert rule_issues(Rule(id="r", name="Empty")) == ["Empty: Add at least one condition."]
    incomplete = cond(Arithmetic(left=field("ttc")), "==", text("1"))
    rule = Rule(id="r", name="Sum", conditions=[incomplete])
    assert rule_issues(rule) == ["Sum: Condition 1: Choose both fields of the arithmetic."]


def test_conditions_round_trip_in_the_wire_shape():
    wire = {
        "id": "c",
        "left": {"kind": "arithmetic", "op": "+", "left": {"kind": "field", "field": "ht"},
                 "right": {"kind": "field", "field": "tva"}},
        "operator": "==",
        "right": {"kind": "field", "field": "ttc"},
    }  # fmt: skip
    condition = Condition.model_validate(wire)
    assert isinstance(condition.left, Arithmetic)
    assert condition.model_dump() == wire


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
    values = field_values(rows, rule=cross, doc_types_by_id=types)
    assert values["invoice__total"] == (6000, "number")
    assert "total" not in values  # ambiguous across the two documents
    assert values["vendor"] == ("Acme", "verbatim-string")  # only one document has it
    [outcome] = evaluate_rules([cross], rows, doc_types_by_id=types)
    assert outcome.status == "passed"


# --- Fixed in 1.0 (each was a silent wrong answer) ---


def test_in_with_one_value_is_membership_not_a_substring_or_an_error():
    numbers = {"n": (5.0, "number")}
    words = {"w": ("apple", "verbatim-string")}
    assert check(cond(field("n"), "IN", text("5")), numbers) is True
    assert check(cond(field("n"), "NOT_IN", text("6")), numbers) is True
    assert check(cond(field("w"), "IN", text("pineapple")), words) is False
    assert check(cond(field("w"), "IN", text("pear, apple")), words) is True


def test_dates_and_times_compare_as_dates_not_text():
    when = {"t": ("2024-01-02T10:00:00+05:00", "date-time")}  # 05:00 UTC
    assert check(cond(field("t"), ">", text("2024-01-02T06:00:00Z")), when) is False
    assert check(cond(field("t"), "<", text("2024-01-02T06:00:00+00:00")), when) is True
    assert check(cond(field("t"), ">", text("2023-12-31")), {"t": ("2024-01-01", "date")})
    assert typed("not a date", "date") is None  # mistyped counts as missing
    with pytest.raises(ValueError, match="Invalid isoformat"):
        literal("banana", "date")
    assert condition_issue(cond(field("d"), ">", text("banana")), SchemaTypes(fields={"d": "date"}))


def test_list_fields_only_take_presence_checks():
    schema = SchemaTypes(fields={"tags": "verbatim-string-list", "kinds": "multi-enum"})
    for name in ("tags", "kinds"):
        assert condition_issue(cond(field(name), "==", text("a")), schema)
        assert condition_issue(cond(field(name), "IN", text("a")), schema)
        assert condition_issue(cond(field(name), "EXISTS"), schema) is None


def test_an_aggregate_over_a_table_not_extracted_is_unknown():
    count = cond(Aggregate(fn="count_rows_where", table="lines"), "==", text("0"))
    total = cond(Aggregate(fn="sum_rows", table="lines", column="amount"), "==", text("0"))
    missing = {"lines": (None, "object-array")}
    assert check(count, missing) is None  # skipped, not "0 rows: passed"
    assert check(total, missing) is None


def test_prefixed_names_resolve_with_one_document_and_bare_names_when_unique():
    rule = Rule(id="r", conditions=[cond(field("Invoice.total"), "==", text("5"))])
    rows = [("total", 5.0, "Invoice", "number")]
    values = field_values(rows, rule=rule, doc_types_by_id={"d1": "Invoice"})
    assert {"invoice__total", "total"} <= values.keys()
    assert evaluate_rule(rule, values).status == "passed"
    two = [("total", 5.0, "Invoice", "number"), ("total", 6.0, "Receipt", "number")]
    values = field_values(two, rule=rule, doc_types_by_id={"d1": "Invoice", "d2": "Receipt"})
    assert "total" not in values  # ambiguous: name the document
    assert values["receipt__total"] == (6.0, "number")
