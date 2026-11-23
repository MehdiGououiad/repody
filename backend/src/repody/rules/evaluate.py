"""Check rules against extracted fields, and describe or validate their conditions.

Every value is read by its field's declared type (see ``values``); a literal takes the
type of the expression it is compared with.
"""

import json
import math
import operator
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from repody.rules.tables import count_rows, sum_rows
from repody.rules.values import field_key, is_number, literal, typed
from repody.schemas.catalog import NUMBER_TYPES, TABLE_TYPE, is_list_type, operators_for
from repody.schemas.rule import (
    UNARY_OPERATORS,
    Aggregate,
    Arithmetic,
    Condition,
    Expression,
    FieldRef,
    LiteralValue,
    Operand,
    Rule,
)
from repody.schemas.run import RuleStatus

# An extracted field: (key, JSON value or None, document type, declared template type).
FieldRow = tuple[str, Any, str | None, str]
# What a rule can read: field_key -> (value, declared type).
Values = Mapping[str, tuple[Any, str]]

LIST_OPERATORS = frozenset({"IN", "NOT_IN"})


@dataclass(frozen=True, slots=True)
class SchemaTypes:
    """What the schema declares, by ``field_key``: each field's type, and each table's columns."""

    fields: Mapping[str, str] = field(default_factory=dict)
    columns: Mapping[str, Mapping[str, str]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RuleOutcome:
    rule: Rule
    status: RuleStatus
    detail: str
    expression: str
    affected_fields: list[str]


def _text(value: str) -> str:
    """Text as rules compare it: case and runs of spaces ignored (``ACME  SARL`` is ``Acme SARL``),
    as the same company is often written both ways on two documents."""
    return " ".join(value.split()).casefold()


def _equal(left: Any, right: Any) -> bool:
    if is_number(left) and is_number(right):
        return math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-9)
    if isinstance(left, str) and isinstance(right, str):
        return _text(left) == _text(right)
    return left == right


def _contains(left: Any, right: Any) -> bool:
    """``IN``: one of the listed values, or part of a text field's value (case ignored)."""
    if isinstance(right, str):
        return _text(str(left)) in _text(right)
    return any(_equal(left, value) for value in right)


_COMPARE: dict[str, Callable[[Any, Any], bool]] = {
    "==": _equal,
    "!=": lambda a, b: not _equal(a, b),
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "IN": _contains,
    "NOT_IN": lambda a, b: not _contains(a, b),
}
_ARITHMETIC: dict[str, Callable[[float, float], float]] = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
}


# --- What a condition reads, and how it reads aloud ---


def condition_fields(condition: Condition) -> list[str]:
    """Field names a condition reads, in order."""
    match condition.left:
        case FieldRef(field=name):
            names = [name]
        case Arithmetic(left=a, right=b):
            names = [a.field, b.field]
        case Aggregate(table=table):
            names = [table]
    if isinstance(condition.right, FieldRef):
        names.append(condition.right.field)
    return list(dict.fromkeys(name for name in names if name.strip()))


def _describe_expression(expression: Expression) -> str:
    match expression:
        case FieldRef(field=name):
            return name or "?"
        case Arithmetic(op=op, left=a, right=b):
            return f"{a.field or '?'} {op} {b.field or '?'}"
        case Aggregate(fn=fn, table=table, column=column):
            args = [table] if fn == "count_rows_where" else [table, column]
            if fn != "sum_rows":
                args += [expression.filter_column, f'contains "{expression.filter_contains}"']
            return f"{fn}({', '.join(args)})"


def _describe_operand(operand: Operand | None) -> str:
    match operand:
        case None:
            return "?"
        case FieldRef(field=name):
            return name or "?"
        case LiteralValue(value=value):
            try:
                float(value)
            except ValueError:
                return json.dumps(value, ensure_ascii=False)
            return value


def describe(condition: Condition) -> str:
    """Readable form of a condition, e.g. ``subtotal + tax == total``."""
    left = _describe_expression(condition.left)
    if condition.operator in UNARY_OPERATORS:
        return f"{left} {condition.operator}"
    return f"{left} {condition.operator} {_describe_operand(condition.right)}"


def _left_type(condition: Condition, type_of: Callable[[str], str | None]) -> str | None:
    """The type the left side produces: aggregates and arithmetic give numbers."""
    if isinstance(condition.left, FieldRef):
        return type_of(field_key(condition.left.field))
    return "number"


# --- Validation (what keeps a rule from being saved) ---


def _incomplete(condition: Condition) -> str | None:
    """A part of the condition the builder left empty."""
    match condition.left:
        case FieldRef(field=name) if not name.strip():
            return "Choose a field on the left."
        case Arithmetic(left=a, right=b) if not (a.field.strip() and b.field.strip()):
            return "Choose both fields of the arithmetic."
        case Aggregate(table=table) if not table.strip():
            return "Choose the table field to aggregate."
        case Aggregate(fn=fn, column=column) if fn != "count_rows_where" and not column.strip():
            return "Choose the column to sum."
    right = condition.right
    filled = right is not None and (
        right.field.strip() if isinstance(right, FieldRef) else right.value.strip()
    )
    if condition.operator not in UNARY_OPERATORS and not filled:
        return "Enter a value or field on the right."
    return None


def _unknown(condition: Condition, schema: SchemaTypes) -> str | None:
    for name in condition_fields(condition):
        if field_key(name) not in schema.fields:
            return f"Unknown field {name}: it is not in the document schemas."
    if isinstance(agg := condition.left, Aggregate):
        columns = schema.columns.get(field_key(agg.table), {})
        for column in (agg.column, agg.filter_column):
            if column.strip() and field_key(column) not in columns:
                return f"Unknown column {column} in {agg.table}."
    return None


def _mistyped(condition: Condition, schema: SchemaTypes) -> str | None:
    """An operator or literal that does not fit the types of the fields it reads."""
    match condition.left:
        case Aggregate(table=table, column=column, fn=fn):
            if schema.fields[field_key(table)] != TABLE_TYPE:
                return f"{table} is not an object-array field."
            column_type = schema.columns.get(field_key(table), {}).get(field_key(column))
            if fn != "count_rows_where" and column_type not in NUMBER_TYPES:
                return f"Sums need a number column; {column} is {column_type}."
        case Arithmetic(left=a, right=b):
            for ref in (a, b):
                if schema.fields.get(field_key(ref.field)) not in NUMBER_TYPES:
                    return f"Arithmetic needs number fields; {ref.field} is not a number."
    left_type = _left_type(condition, schema.fields.get)
    if left_type and condition.operator not in operators_for(left_type):
        if is_list_type(left_type) or left_type == TABLE_TYPE:
            return f"{left_type} fields are lists: check them with EXISTS or IS_EMPTY."
        return f"{condition.operator} compares numbers or dates; the left side is {left_type}."
    right = condition.right
    if isinstance(right, LiteralValue) and condition.operator not in UNARY_OPERATORS:
        parts = right.value.split(",") if condition.operator in LIST_OPERATORS else [right.value]
        try:
            for part in parts:
                literal(part, left_type)
        except ValueError:
            return f"{right.value!r} is not a {left_type} value."
    return None


def condition_issue(condition: Condition, schema: SchemaTypes | None = None) -> str | None:
    """Why a condition cannot be saved, or None. ``schema`` adds the checks that need it:
    known fields and columns, and operators that fit their types."""
    issue = _incomplete(condition)
    if issue is None and schema is not None:
        issue = _unknown(condition, schema) or _mistyped(condition, schema)
    return issue


def rule_issues(rule: Rule, schema: SchemaTypes | None = None) -> list[str]:
    """Problems that keep a rule from being saved, prefixed with the rule's name."""
    label = rule.name.strip() or "Unnamed rule"
    if not rule.conditions:
        return [f"{label}: Add at least one condition."]
    return [
        f"{label}: Condition {index}: {issue}"
        for index, condition in enumerate(rule.conditions, start=1)
        if (issue := condition_issue(condition, schema))
    ]


# --- Evaluation ---


def field_values(
    rows: Iterable[FieldRow], *, rule: Rule, doc_types_by_id: dict[str, str]
) -> dict[str, tuple[Any, str]]:
    """Fields a rule can read, by ``field_key``: ``<document_type>.<field>`` always, and the bare
    name when exactly one of the rule's documents has it (the names the builder offers and saving
    accepts, ``app.workflows.schema_types``)."""
    allowed = {doc_types_by_id[d] for d in rule.applies_to if d in doc_types_by_id}
    values: dict[str, tuple[Any, str]] = {}
    bare: dict[str, list[tuple[Any, str]]] = {}
    for key, value, doc_type, field_type in rows:
        if not key or (allowed and doc_type not in allowed):
            continue
        if doc_type:
            values[field_key(f"{doc_type}.{key}")] = (value, field_type)
        bare.setdefault(field_key(key), []).append((value, field_type))
    for key, found in bare.items():
        if len(found) == 1:
            values[key] = found[0]
    return values


def _field(name: str, values: Values) -> Any:
    key = field_key(name)
    if key not in values:
        raise LookupError(name)
    value, field_type = values[key]
    return typed(value, field_type)


def _left(expression: Expression, values: Values) -> Any:
    match expression:
        case FieldRef(field=name):
            return _field(name, values)
        case Arithmetic(op=op, left=a, right=b):
            left, right = _field(a.field, values), _field(b.field, values)
            if left is None or right is None:
                return None
            if not (is_number(left) and is_number(right)):
                raise TypeError("arithmetic needs number fields")
            return _ARITHMETIC[op](left, right)
        case Aggregate():
            table = _field(expression.table, values)
            if not isinstance(table, list):  # not extracted: the aggregate is unknown, not 0
                return None
            if expression.fn == "count_rows_where":
                return count_rows(table, expression.filter_column, expression.filter_contains)
            if expression.fn == "sum_rows_where":
                return sum_rows(
                    table, expression.column, expression.filter_column, expression.filter_contains
                )
            return sum_rows(table, expression.column)


def check(condition: Condition, values: Values) -> bool | None:
    """True or False, or None when a value it needs was not extracted.

    Raises LookupError for an unknown field, ValueError for a literal that is not of the
    field's type, and TypeError/ZeroDivisionError when the values cannot be compared.
    """
    left = _left(condition.left, values)
    if condition.operator == "EXISTS":
        return left is not None
    if condition.operator == "IS_EMPTY":
        return left is None
    right = condition.right
    if right is None or left is None:
        return None
    left_type = _left_type(condition, lambda key: values[key][1] if key in values else None)
    match right:
        case FieldRef(field=name):
            value: Any = _field(name, values)
        case LiteralValue(value=text) if condition.operator in LIST_OPERATORS:
            value = [literal(part, left_type) for part in text.split(",") if part.strip()]
        case LiteralValue(value=text):
            value = literal(text, left_type)
    if value is None:
        return None
    return _COMPARE[condition.operator](left, value)


def evaluate_rule(rule: Rule, values: Values) -> RuleOutcome:
    failed: list[Condition] = []
    notes: list[str] = []
    skipped = False
    for condition in rule.conditions:
        text = describe(condition)
        try:
            result = check(condition, values)
        except LookupError as exc:
            skipped = True
            notes.append(f"Field not found: {exc.args[0]}. Check it matches a schema field.")
            continue
        except (TypeError, ValueError, ZeroDivisionError) as exc:
            result = False
            notes.append(f"Cannot evaluate {text}: {exc}")
        if result is None:
            skipped = True
            notes.append(f"No value extracted for {text}.")
        elif not result:
            failed.append(condition)
            notes.append(f"Not satisfied: {text}")

    if failed:
        status: RuleStatus = "failed"
    elif skipped or not rule.conditions:
        status = "skipped"
    else:
        status = "passed"
    affected = failed or rule.conditions
    return RuleOutcome(
        rule=rule,
        status=status,
        detail=" ".join(notes) or ("All conditions hold." if rule.conditions else "No conditions."),
        expression=" and ".join(describe(c) for c in rule.conditions),
        affected_fields=list(dict.fromkeys(f for c in affected for f in condition_fields(c))),
    )


def evaluate_rules(
    rules: list[Rule], rows: Sequence[FieldRow], *, doc_types_by_id: dict[str, str]
) -> list[RuleOutcome]:
    return [
        evaluate_rule(rule, field_values(rows, rule=rule, doc_types_by_id=doc_types_by_id))
        for rule in rules
    ]
