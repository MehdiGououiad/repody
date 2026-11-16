"""Logic rules as the workflow builder edits them and the database stores them.

A condition compares a left-hand expression with an operand::

    left (field | arithmetic | aggregate)  operator  right (field | literal)

Each kind of expression carries only the parts it needs, so a stored condition is always
complete in shape; ``repody.rules.evaluate`` checks that its fields exist and fit.
"""

from typing import Annotated, Literal

from pydantic import Field

from repody.schemas.common import CamelModel, Id, Name, Text

Operator = Literal["==", "!=", ">", ">=", "<", "<=", "IN", "NOT_IN", "EXISTS", "IS_EMPTY"]
ArithmeticOp = Literal["+", "-", "*", "/"]
AggregateFn = Literal["sum_rows", "sum_rows_where", "count_rows_where"]
Severity = Literal["reject", "flag"]
Scope = Literal["intra", "cross"]

# Operators that test the left side alone (no right-hand operand).
PRESENCE_OPERATORS: tuple[Operator, ...] = ("EXISTS", "IS_EMPTY")
UNARY_OPERATORS = frozenset(PRESENCE_OPERATORS)


class FieldRef(CamelModel):
    """A schema field: ``total`` or, with several documents, ``invoice.total``."""

    kind: Literal["field"] = "field"
    field: Name = ""


class LiteralValue(CamelModel):
    """A value typed by the user, read as the type of the field it is compared with."""

    kind: Literal["literal"] = "literal"
    value: Text = ""


class Arithmetic(CamelModel):
    """``left op right`` on two number fields."""

    kind: Literal["arithmetic"] = "arithmetic"
    op: ArithmeticOp = "+"
    left: FieldRef = Field(default_factory=FieldRef)
    right: FieldRef = Field(default_factory=FieldRef)


class Aggregate(CamelModel):
    """Sum or count the rows of an object-array field, optionally filtered by a column.

    ``column`` and ``filter_column`` are child field names as written in the schema.
    """

    kind: Literal["aggregate"] = "aggregate"
    fn: AggregateFn = "sum_rows"
    table: Name = ""
    column: Name = ""
    filter_column: Name = ""
    filter_contains: Name = ""


Operand = Annotated[FieldRef | LiteralValue, Field(discriminator="kind")]
Expression = Annotated[FieldRef | Arithmetic | Aggregate, Field(discriminator="kind")]


class Condition(CamelModel):
    id: Id
    left: Expression = Field(default_factory=FieldRef)
    operator: Operator = "=="
    right: Operand | None = None


class Rule(CamelModel):
    """A rule passes when every condition holds on the documents it applies to."""

    id: Id
    name: Name = ""
    scope: Scope = "intra"
    applies_to: list[Id] = Field(default_factory=list, max_length=20)
    severity: Severity = "reject"
    conditions: list[Condition] = Field(default_factory=list, max_length=50)
