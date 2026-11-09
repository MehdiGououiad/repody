"""Check rules against extracted fields, and describe or validate their conditions.

Every value is read by its field's declared type (see ``values``); a literal takes the
type of the field it is compared with.
"""

from __future__ import annotations

import json
import math
import operator
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from repody.rules.tables import count_rows, sum_rows
from repody.rules.values import (
    NUMBER_TYPES,
    ORDERED_TYPES,
    TABLE_TYPE,
    field_key,
    literal,
    typed,
)
from repody.schemas.rule import UNARY_OPERATORS, Condition, Operand, Rule
from repody.schemas.run import RuleStatus

# An extracted field: (key, JSON value or None, document type, declared template type).
FieldRow = tuple[str, Any, str | None, str]
# What a rule can read: field_key -> (value, declared type).
Values = Mapping[str, tuple[Any, str]]

ORDERING_OPERATORS = frozenset({">", ">=", "<", "<="})


def _equal(left: Any, right: Any) -> bool:
    if isinstance(left, float | int) and isinstance(right, float | int):
        return math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-9)
    return left == right


def _contains(left: Any, right: Any) -> bool:
    return str(left) in right if isinstance(right, str) else left in right


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
_ARITHMETIC: dict[str, Callable[[Any, Any], Any]] = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
}


@dataclass(frozen=True, slots=True)
class RuleOutcome:
    rule: Rule
    status: RuleStatus
    detail: str
    expression: str
    affected_fields: list[str]


def field_values(
    rows: Iterable[FieldRow], *, rule: Rule, doc_types_by_id: dict[str, str], multi_document: bool
) -> dict[str, tuple[Any, str]]:
    """Fields a rule can read, by ``field_key``.

    With several documents a field is ``<document_type>.<field>``; the bare name also works
    when exactly one of the rule's documents has it.
    """
    allowed = {doc_types_by_id[d] for d in rule.applies_to if d in doc_types_by_id}
    values: dict[str, tuple[Any, str]] = {}
    bare: dict[str, list[tuple[Any, str]]] = {}
    for key, value, doc_type, field_type in rows:
        if not key or (multi_document and allowed and doc_type not in allowed):
            continue
        if multi_document and doc_type:
            values[field_key(f"{doc_type}.{key}")] = (value, field_type)
        bare.setdefault(field_key(key), []).append((value, field_type))
    for key, found in bare.items():
        if not multi_document or len(found) == 1:
            values[key] = found[-1]
    return values


def condition_fields(condition: Condition) -> list[str]:
    """Field names a condition reads, in order."""
    names = [condition.table_aggregate.table_field] if condition.table_aggregate else []
    names += [
        op.value
        for op in (condition.left, condition.left_extra, condition.right)
        if op is not None and op.kind == "field"
    ]
    return list(dict.fromkeys(name for name in names if name.strip()))


def describe(condition: Condition) -> str:
    """Readable form of a condition, e.g. ``subtotal + tax == total``."""
    if agg := condition.table_aggregate:
        args = (
            [agg.table_field]
            if agg.fn == "count_rows_where"
            else [agg.table_field, agg.amount_column]
        )
        if agg.fn != "sum_rows":
            args += [agg.filter_column, f'contains "{agg.filter_contains}"']
        left = f"{agg.fn}({', '.join(args)})"
    else:
        left = _describe(condition.left)
    if condition.arithmetic_op and condition.left_extra:
        left = f"{left} {condition.arithmetic_op} {_describe(condition.left_extra)}"
    if condition.operator in UNARY_OPERATORS:
        return f"{left} {condition.operator}"
    return f"{left} {condition.operator} {_describe(condition.right)}"


def _describe(operand: Operand | None) -> str:
    if operand is None:
        return "?"
    if operand.kind == "field":
        return operand.value
    try:
        float(operand.value)
    except ValueError:
        return json.dumps(operand.value, ensure_ascii=False)
    return operand.value


def _left_type(condition: Condition, type_of: Callable[[str], str | None]) -> str | None:
    """The type the left side produces: aggregates and arithmetic give numbers."""
    if condition.table_aggregate or condition.arithmetic_op:
        return "number"
    return type_of(field_key(condition.left.value))


def condition_issue(condition: Condition, types: Mapping[str, str] | None = None) -> str | None:
    """Why a condition cannot be saved, or None. ``types`` (field_key -> template type) adds
    the checks that need the schema: known fields, and operators that fit their types."""
    agg = condition.table_aggregate
    if agg:
        if not agg.table_field.strip():
            return "Choose the table field to aggregate."
        if agg.fn != "count_rows_where" and not agg.amount_column.strip():
            return "Choose the column to sum."
    elif not condition.left.value.strip():
        return "Choose a field on the left."
    if condition.arithmetic_op and not (
        condition.left_extra and condition.left_extra.value.strip()
    ):
        return "Choose the second operand of the arithmetic."
    if condition.operator not in UNARY_OPERATORS and not (
        condition.right and condition.right.value.strip()
    ):
        return "Enter a value or field on the right."
    if types is None:
        return None

    for name in condition_fields(condition):
        if field_key(name) not in types:
            return f"Unknown field {name}: it is not in the document schemas."
    if agg and types[field_key(agg.table_field)] != TABLE_TYPE:
        return f"{agg.table_field} is not an object-array field."
    if condition.arithmetic_op and not agg:
        for operand in (condition.left, condition.left_extra):
            if operand and types.get(field_key(operand.value)) not in NUMBER_TYPES:
                return f"Arithmetic needs number fields; {operand.value} is not a number."
    left_type = _left_type(condition, types.get)
    if condition.operator in ORDERING_OPERATORS and left_type not in ORDERED_TYPES:
        return f"{condition.operator} compares numbers or dates; the left side is {left_type}."
    right = condition.right
    if right is not None and right.kind == "literal" and condition.operator not in UNARY_OPERATORS:
        parts = right.value.split(",") if condition.operator in ("IN", "NOT_IN") else [right.value]
        try:
            for part in parts:
                literal(part, left_type)
        except ValueError:
            return f"{right.value!r} is not a {left_type} value."
    return None


def rule_issues(rule: Rule, types: Mapping[str, str] | None = None) -> list[str]:
    """Problems that keep a rule from being saved, prefixed with the rule's name."""
    label = rule.name.strip() or rule.id
    if not rule.conditions:
        return [f"{label}: Add at least one condition."]
    return [
        f"{label}: Condition {index}: {issue}"
        for index, condition in enumerate(rule.conditions, start=1)
        if (issue := condition_issue(condition, types))
    ]


def _field(name: str, values: Values) -> Any:
    key = field_key(name)
    if key not in values:
        raise LookupError(name)
    value, field_type = values[key]
    return typed(value, field_type)


def _operand(operand: Operand, values: Values, as_type: str | None) -> Any:
    if operand.kind == "literal":
        return literal(operand.value, as_type)
    return _field(operand.value, values)


def _left(condition: Condition, values: Values) -> Any:
    if agg := condition.table_aggregate:
        table = _field(agg.table_field, values)
        if agg.fn == "count_rows_where":
            return count_rows(table, agg.filter_column, agg.filter_contains)
        if agg.fn == "sum_rows_where":
            return sum_rows(table, agg.amount_column, agg.filter_column, agg.filter_contains)
        return sum_rows(table, agg.amount_column)
    left = _field(condition.left.value, values)
    if condition.arithmetic_op and condition.left_extra and left is not None:
        extra = _operand(condition.left_extra, values, "number")
        if extra is None:
            return None
        if not all(isinstance(v, int | float) and not isinstance(v, bool) for v in (left, extra)):
            raise TypeError("arithmetic needs number fields")
        return _ARITHMETIC[condition.arithmetic_op](left, extra)
    return left


def check(condition: Condition, values: Values) -> bool | None:
    """True or False, or None when a value it needs was not extracted.

    Raises LookupError for an unknown field, ValueError for a literal that is not of the
    field's type, and TypeError/ZeroDivisionError when the values cannot be compared.
    """
    left = _left(condition, values)
    if condition.operator == "EXISTS":
        return left is not None
    if condition.operator == "IS_EMPTY":
        return left is None
    right = condition.right
    if right is None or left is None:
        return None
    left_type = _left_type(condition, lambda key: values[key][1] if key in values else None)
    if condition.operator in ("IN", "NOT_IN") and right.kind == "literal" and "," in right.value:
        value: Any = [literal(part, left_type) for part in right.value.split(",") if part.strip()]
    else:
        value = _operand(right, values, left_type)
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
    rules: list[Rule],
    rows: Sequence[FieldRow],
    *,
    doc_types_by_id: dict[str, str],
    multi_document: bool,
) -> list[RuleOutcome]:
    return [
        evaluate_rule(
            rule,
            field_values(
                rows, rule=rule, doc_types_by_id=doc_types_by_id, multi_document=multi_document
            ),
        )
        for rule in rules
    ]
