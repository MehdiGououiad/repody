"""Check rules against extracted field values, and describe or validate their conditions."""

from __future__ import annotations

import json
import math
import operator
from collections.abc import Awaitable, Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from repody.rules.models import UNARY_OPERATORS, Condition, Operand, Rule
from repody.rules.tables import count_rows, sum_rows
from repody.rules.values import coerce, field_key, parse_numeric_value

Status = Literal["passed", "failed", "skipped"]

# An extracted field: (key, value, document type).
FieldRow = tuple[str, str, str | None]


def _equal(left: Any, right: Any) -> bool:
    if isinstance(left, float | int) and isinstance(right, float | int):
        return math.isclose(left, right, abs_tol=0.005)
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
    status: Status
    detail: str
    expression: str
    affected_fields: list[str]


class _UnknownFieldError(LookupError):
    pass


def field_values(
    rows: Iterable[FieldRow], *, rule: Rule, doc_types_by_id: dict[str, str], multi_document: bool
) -> dict[str, str]:
    """Values a rule can read, by ``field_key``.

    With several documents a field is ``<document_type>.<field>``; the bare name also works
    when exactly one of the rule's documents has it.
    """
    allowed = {doc_types_by_id[d] for d in rule.applies_to if d in doc_types_by_id}
    values: dict[str, str] = {}
    bare: dict[str, list[str]] = {}
    for key, value, doc_type in rows:
        if not key or (multi_document and allowed and doc_type not in allowed):
            continue
        if multi_document and doc_type:
            values[field_key(f"{doc_type}.{key}")] = value
        bare.setdefault(field_key(key), []).append(value)
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
        if op is not None and op.kind == "field" and op.value.strip()
    ]
    return list(dict.fromkeys(name for name in names if name.strip()))


def describe(condition: Condition) -> str:
    """Readable form of a condition, e.g. ``subtotal + tax == total``."""
    if agg := condition.table_aggregate:
        args = (
            [agg.table_field, agg.amount_column]
            if agg.fn != "count_rows_where"
            else [agg.table_field]
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
    if operand.kind == "field" or parse_numeric_value(operand.value) is not None:
        return operand.value
    return json.dumps(operand.value, ensure_ascii=False)


def condition_issue(condition: Condition) -> str | None:
    """Why a condition cannot be checked yet, or None when it is complete."""
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
    return None


def rule_issues(rule: Rule) -> list[str]:
    """Problems that keep a rule from being saved, prefixed with the rule's name."""
    label = rule.name.strip() or rule.id
    if not rule.conditions:
        return [f"{label}: Add at least one condition."]
    return [
        f"{label}: Condition {index}: {issue}"
        for index, condition in enumerate(rule.conditions, start=1)
        if (issue := condition_issue(condition))
    ]


def _read(operand: Operand, values: dict[str, str]) -> Any:
    if operand.kind == "literal":
        return coerce(operand.value)
    key = field_key(operand.value)
    if key not in values:
        raise _UnknownFieldError(operand.value)
    return coerce(values[key])


def _left(condition: Condition, values: dict[str, str]) -> Any:
    if agg := condition.table_aggregate:
        key = field_key(agg.table_field)
        if key not in values:
            raise _UnknownFieldError(agg.table_field)
        if agg.fn == "count_rows_where":
            return count_rows(values[key], agg.filter_column, agg.filter_contains)
        if agg.fn == "sum_rows_where":
            return sum_rows(values[key], agg.amount_column, agg.filter_column, agg.filter_contains)
        return sum_rows(values[key], agg.amount_column)
    left = _read(condition.left, values)
    if condition.arithmetic_op and condition.left_extra and left is not None:
        extra = _read(condition.left_extra, values)
        if extra is None:
            return None
        return round(_ARITHMETIC[condition.arithmetic_op](left, extra), 2)
    return left


def _right(condition: Condition, values: dict[str, str]) -> Any:
    right = condition.right
    if right is None:
        return None
    if condition.operator in ("IN", "NOT_IN") and right.kind == "literal" and "," in right.value:
        return [coerce(part) for part in right.value.split(",") if part.strip()]
    return _read(right, values)


def check(condition: Condition, values: dict[str, str]) -> bool | None:
    """True or False, or None when a value it needs was not extracted.

    Raises LookupError for an unknown field and TypeError/ZeroDivisionError when the
    values cannot be compared.
    """
    left = _left(condition, values)
    if condition.operator == "EXISTS":
        return left is not None
    if condition.operator == "IS_EMPTY":
        return left is None
    right = _right(condition, values)
    if left is None or right is None:
        return None
    return _COMPARE[condition.operator](left, right)


def evaluate_rule(rule: Rule, values: dict[str, str]) -> RuleOutcome:
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
        except (TypeError, ZeroDivisionError) as exc:
            result = False
            notes.append(f"Cannot evaluate {text}: {exc}")
        if result is None:
            skipped = True
            notes.append(f"No value extracted for {text}.")
        elif not result:
            failed.append(condition)
            notes.append(f"Not satisfied: {text}")

    if failed:
        status: Status = "failed"
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


async def evaluate_rules(
    rules: list[Rule],
    rows: Sequence[FieldRow],
    *,
    doc_types_by_id: dict[str, str],
    multi_document: bool,
    on_rule_start: Callable[[Rule], Awaitable[None]] | None = None,
) -> list[RuleOutcome]:
    outcomes: list[RuleOutcome] = []
    for rule in rules:
        if on_rule_start is not None:
            await on_rule_start(rule)
        values = field_values(
            rows, rule=rule, doc_types_by_id=doc_types_by_id, multi_document=multi_document
        )
        outcomes.append(evaluate_rule(rule, values))
    return outcomes
