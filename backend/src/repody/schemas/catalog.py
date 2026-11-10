"""The NuExtract template types a schema field can have, and what rules can do with each.

The single source of this taxonomy: the API validates fields with it, the rules engine
compares values by it, and the builder reads it from ``GET /v1/catalog``.
https://huggingface.co/numind/NuExtract3/blob/main/TYPES.md
"""

import re
from typing import Annotated, Literal

from pydantic import AfterValidator, Field

from repody.schemas.common import CamelModel
from repody.schemas.rule import PRESENCE_OPERATORS, Operator

TypeGroup = Literal["common", "structure", "advanced"]

LEAF_TYPES: dict[str, TypeGroup] = {
    "verbatim-string": "common",
    "string": "common",
    "integer": "common",
    "number": "common",
    "date": "common",
    "time": "common",
    "date-time": "common",
    "boolean": "common",
    "currency": "common",
    "email-address": "common",
    "phone-number": "common",
    "duration": "advanced",
    "country": "advanced",
    "language": "advanced",
    "language-tag": "advanced",
    "script": "advanced",
    "url": "advanced",
    "iban": "advanced",
    "bic": "advanced",
    "unit-code": "advanced",
}
STRUCTURE_TYPES = ("object", "object-array", "enum", "multi-enum")
DEFAULT_TYPE = "verbatim-string"
LIST_SUFFIX = "-list"  # platform spelling of a NuExtract list: `number-list` is `["number"]`
# Parameterised NuExtract types such as `region:FR`.
_PARAMETERISED = re.compile(r"^[a-z][a-z-]*:[A-Za-z0-9_-]+$")

_SPACES = re.compile(r"\s+")


def field_key(name: str) -> str:
    """Canonical name of a field: ``Total  Amount`` -> ``total_amount``, ``a.b`` -> ``a__b``.

    Rules address fields by it, and two fields of one schema level may not share it. The
    builder matches field names with the same rule (``lib/rules/field-key.ts``).
    """
    return _SPACES.sub("_", name.strip().lower()).replace(".", "__")


def is_empty(value: object) -> bool:
    """Whether an extracted value counts as not extracted: null, empty text, list or object."""
    return value is None or value in ("", [], {})


def is_list_type(template_type: str) -> bool:
    """Types whose value is a JSON list of values (not a table): ``<type>-list``, multi-enum."""
    return template_type == "multi-enum" or scalar_type(template_type) != template_type


NUMBER_TYPES = frozenset({"number", "integer"})
TEMPORAL_TYPES = frozenset({"date", "date-time", "time"})  # ISO 8601, compared as dates
ORDERED_TYPES = NUMBER_TYPES | TEMPORAL_TYPES
TABLE_TYPE = "object-array"

EQUALITY_OPERATORS: tuple[Operator, ...] = ("==", "!=", "IN", "NOT_IN")
ORDERING_OPERATORS: tuple[Operator, ...] = (">", ">=", "<", "<=")


def scalar_type(template_type: str) -> str:
    """The type without its ``-list`` suffix."""
    if template_type.endswith(LIST_SUFFIX) and template_type != LIST_SUFFIX:
        return template_type.removesuffix(LIST_SUFFIX)
    return template_type


def _check_template_type(value: str) -> str:
    value = value.strip() or DEFAULT_TYPE
    scalar = scalar_type(value)
    if value in STRUCTURE_TYPES or scalar in LEAF_TYPES or _PARAMETERISED.match(scalar):
        return value
    raise ValueError(f"Unknown template type {value!r}.")


TemplateType = Annotated[str, AfterValidator(_check_template_type)]


def operators_for(template_type: str) -> list[Operator]:
    """The operators a condition can apply to a value of this type: every type takes presence
    checks; lists and tables only those (aggregate a table to compare it); numbers and dates
    are also ordered. Saving a rule checks it (rules.evaluate), and the builder offers these."""
    if is_list_type(template_type) or template_type in (TABLE_TYPE, "object"):
        return list(PRESENCE_OPERATORS)
    ordered = ORDERING_OPERATORS if template_type in ORDERED_TYPES else ()
    return [*EQUALITY_OPERATORS, *ordered, *PRESENCE_OPERATORS]


class TemplateTypeInfo(CamelModel):
    value: str
    group: TypeGroup
    listable: bool


class Catalog(CamelModel):
    """What the builder offers: field types, and which of them rules can order or add."""

    template_types: list[TemplateTypeInfo]
    default_type: str
    number_types: list[str]
    ordered_types: list[str]
    table_type: str
    operators_by_type: dict[str, list[Operator]] = Field(
        description="Operators each type takes (lists as `<type>-list`); other types: the default's."
    )
    presence_operators: list[Operator] = Field(description="Operators with no right-hand side.")


def catalog() -> Catalog:
    return Catalog(
        template_types=[
            *(TemplateTypeInfo(value=t, group=g, listable=True) for t, g in LEAF_TYPES.items()),
            *(
                TemplateTypeInfo(value=t, group="structure", listable=False)
                for t in STRUCTURE_TYPES
            ),
        ],
        default_type=DEFAULT_TYPE,
        number_types=sorted(NUMBER_TYPES),
        ordered_types=sorted(ORDERED_TYPES),
        table_type=TABLE_TYPE,
        operators_by_type={
            t: operators_for(t)
            for t in [
                *LEAF_TYPES,
                *(f"{leaf}{LIST_SUFFIX}" for leaf in LEAF_TYPES),
                *STRUCTURE_TYPES,
            ]
        },
        presence_operators=list(PRESENCE_OPERATORS),
    )
