"""NuExtract's JSON answer as one value per schema leaf, for the report and rules.

``object`` fields expand to ``parent.child`` keys; an ``object-array`` stays one leaf whose
value is its list of rows. Values keep the JSON type the model returned; a field the model
left out (or returned empty) is None.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from repody.schemas.workflow import SchemaField


@dataclass(frozen=True, slots=True)
class FieldValue:
    key: str
    description: str
    type: str
    value: Any

    @property
    def extracted(self) -> bool:
        return self.value is not None


def leaves(
    fields: list[SchemaField], data: Any = None, prefix: str = ""
) -> Iterator[tuple[str, SchemaField, Any]]:
    """``(key, field, value in data)`` for every leaf of the schema."""
    for field in fields:
        if not field.name:
            continue
        key = f"{prefix}{field.name}"
        value = data.get(field.name) if isinstance(data, dict) else None
        if field.template_type == "object" and field.children:
            yield from leaves(field.children, value, f"{key}.")
        else:
            yield key, field, value


def _clean(value: Any) -> Any:
    if isinstance(value, str):
        value = value.strip()
    return None if value in ("", [], {}) else value


def leaf_values(fields: list[SchemaField], answer: str | None) -> list[FieldValue]:
    """Every leaf with its value from the model's JSON ``answer``."""
    try:
        data = json.loads(answer or "")
    except json.JSONDecodeError:
        data = None
    return [
        FieldValue(
            key=key, description=field.description, type=field.template_type, value=_clean(value)
        )
        for key, field, value in leaves(fields, data)
    ]
