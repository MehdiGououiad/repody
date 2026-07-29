"""Project official NuExtract JSON onto schema leaves for UI and rules.

Official docs: the model returns JSON matching the template. That object is the
source of truth (stored as ``rawText``). This module only flattens leaves into
``ExtractedFieldResult`` for the workbench UI and rules engine.
"""

from __future__ import annotations

import json
from typing import Any

from audit_workbench.extraction.nuextract import resolve_template_type
from audit_workbench.extraction.schema import (
    SchemaFieldSpec,
    is_nested_object_group,
    iter_extraction_leaves,
)
from audit_workbench.extraction.types import ExtractedFieldResult

MISSING = "—"


def fields_from_nuextract_json(
    raw: str, schema: list[SchemaFieldSpec]
) -> list[ExtractedFieldResult]:
    """Map NuExtract template JSON onto every schema leaf (missing → ``—``)."""
    data = _parse_json_object(raw)
    values = _collect_leaf_values(data, schema)
    out: list[ExtractedFieldResult] = []
    for key, spec in iter_extraction_leaves(schema):
        if key in values:
            out.append(_leaf_result(key, spec, values[key]))
        else:
            out.append(_leaf_result(key, spec, None))
    return out


def _parse_json_object(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _collect_leaf_values(
    data: dict[str, Any], schema: list[SchemaFieldSpec]
) -> dict[str, Any]:
    """Walk schema against the model object; keys are dotted paths."""
    out: dict[str, Any] = {}

    def walk(field: SchemaFieldSpec, value: Any, prefix: str) -> None:
        name = field.name.strip()
        if not name:
            return
        key = f"{prefix}.{name}" if prefix else name
        if is_nested_object_group(field):
            nested = value if isinstance(value, dict) else {}
            for child in field.children or []:
                child_name = child.name.strip()
                walk(child, nested.get(child_name) if child_name else None, key)
            return
        out[key] = value

    for field in schema:
        name = field.name.strip()
        if not name:
            continue
        walk(field, data.get(name), "")
    return out


def _leaf_result(
    key: str, spec: SchemaFieldSpec, value: Any
) -> ExtractedFieldResult:
    text, extracted = _encode_leaf(value)
    return ExtractedFieldResult(
        key=key,
        description=spec.description,
        value=text,
        type=resolve_template_type(spec.name, spec.description, spec.template_type),
        confidence=None,
        extracted=extracted,
    )


def _encode_leaf(value: Any) -> tuple[str, bool]:
    """Store leaf as a string for UI/rules; preserve JSON for non-strings."""
    if value is None:
        return MISSING, False
    if isinstance(value, str):
        text = value.strip() or MISSING
        return text, text != MISSING
    return json.dumps(value, ensure_ascii=False), True
