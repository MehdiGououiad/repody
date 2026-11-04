"""Logic rules as the workflow builder edits them and the database stores them."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from repody.schemas.common import CamelModel

Operator = Literal["==", "!=", ">", ">=", "<", "<=", "IN", "NOT_IN", "EXISTS", "IS_EMPTY"]
ArithmeticOp = Literal["+", "-", "*", "/"]
AggregateFn = Literal["sum_rows", "sum_rows_where", "count_rows_where"]
Severity = Literal["reject", "flag"]
Scope = Literal["intra", "cross"]

# Operators that test the left side alone.
UNARY_OPERATORS = frozenset({"EXISTS", "IS_EMPTY"})


class Operand(CamelModel):
    """A field reference (``total`` or ``invoice.total``) or a literal typed by the user."""

    kind: Literal["field", "literal"]
    value: str = ""


class TableAggregate(CamelModel):
    """Sum or count rows of an object-array field (optionally filtered by a column)."""

    fn: AggregateFn
    table_field: str = ""
    amount_column: str = ""
    filter_column: str = ""
    filter_contains: str = ""


class Condition(CamelModel):
    """``left [arithmetic_op left_extra] operator right``; ``table_aggregate`` replaces ``left``."""

    id: str
    left: Operand
    operator: Operator = "=="
    right: Operand | None = None
    arithmetic_op: ArithmeticOp | None = None
    left_extra: Operand | None = None
    table_aggregate: TableAggregate | None = None


class Rule(CamelModel):
    """A rule passes when every condition holds on the documents it applies to."""

    id: str
    name: str = ""
    scope: Scope = "intra"
    applies_to: list[str] = Field(default_factory=list)
    severity: Severity = "reject"
    conditions: list[Condition] = Field(default_factory=list)
