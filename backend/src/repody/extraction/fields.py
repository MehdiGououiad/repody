"""Flatten NuExtract's JSON answer into one value per schema leaf, for the report and rules.

``object`` fields expand to ``parent.child`` keys; an ``object-array`` stays one leaf whose
value is its JSON table. Lists and tables are stored as JSON text.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from repody.rules.values import MISSING
from repody.schemas.workflow import SchemaField


@dataclass(frozen=True, slots=True)
class FieldValue:
    key: str
    description: str
    type: str
    value: str

    @property
    def extracted(self) -> bool:
        return self.value != MISSING


def leaf_values(fields: list[SchemaField], answer: str | None) -> list[FieldValue]:
    """Every leaf with its value from ``answer`` (``MISSING`` when absent or no answer)."""
    try:
        data = json.loads(answer or "")
    except json.JSONDecodeError:
        data = {}
    return list(_leaves(fields, data if isinstance(data, dict) else {}, ""))


def _leaves(fields: list[SchemaField], data: dict[str, Any], prefix: str) -> Iterator[FieldValue]:
    for field in fields:
        if not field.name:
            continue
        key = f"{prefix}{field.name}"
        value = data.get(field.name)
        if field.template_type == "object" and field.children:
            yield from _leaves(field.children, value if isinstance(value, dict) else {}, f"{key}.")
            continue
        if isinstance(value, str):
            text = value.strip() or MISSING
        else:
            text = MISSING if value is None else json.dumps(value, ensure_ascii=False)
        yield FieldValue(
            key=key, description=field.description, type=field.template_type, value=text
        )
