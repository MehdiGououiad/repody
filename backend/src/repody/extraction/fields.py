"""Project NuExtract's JSON answer onto schema leaves for the UI and rules.

The model returns JSON shaped like the template; that object is the source of truth
(stored as ``rawText``). This only flattens it into one ``ExtractedFieldResult`` per leaf.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from repody.extraction.types import ExtractedFieldResult, SchemaFieldSpec
from repody.rules.value_coercion import MISSING


def fields_from_nuextract_json(
    raw: str, schema: list[SchemaFieldSpec]
) -> list[ExtractedFieldResult]:
    """Every schema leaf with its value from the model JSON (missing -> ``MISSING``)."""
    try:
        data = json.loads(raw or "")
    except json.JSONDecodeError:
        data = {}
    return list(_leaves(schema, data if isinstance(data, dict) else {}, ""))


def _leaves(
    schema: list[SchemaFieldSpec], data: dict[str, Any], prefix: str
) -> Iterator[ExtractedFieldResult]:
    for field in schema:
        if not field.name:
            continue
        key = f"{prefix}.{field.name}" if prefix else field.name
        value = data.get(field.name)
        if field.template_type == "object" and field.children:
            yield from _leaves(field.children, value if isinstance(value, dict) else {}, key)
            continue
        # Strings are stored as-is; lists / objects (tables) as JSON.
        if isinstance(value, str):
            text = value.strip() or MISSING
        else:
            text = MISSING if value is None else json.dumps(value, ensure_ascii=False)
        yield ExtractedFieldResult(
            key=key,
            description=field.description,
            value=text,
            type=field.template_type,
            confidence=None,
            extracted=text != MISSING,
        )
