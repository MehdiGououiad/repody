"""Build NuExtract3 JSON templates from workflow schema fields."""

from __future__ import annotations

from typing import Any

from audit_workbench.extraction.base import SchemaFieldSpec
from audit_workbench.extraction.nuextract_types import (
    is_enum_template_type,
    is_list_template_type,
    is_multi_enum_template_type,
    is_object_array_template_type,
    list_template_scalar_type,
    normalize_template_type,
    template_type_to_nuextract_leaf,
)
from audit_workbench.extraction.template_type_inference import resolve_template_type


def build_field_template_node(field: SchemaFieldSpec) -> Any:
    """Recursive NuExtract template node for one schema field."""
    resolved = resolve_template_type(field.name, field.description, field.template_type)

    if is_object_array_template_type(resolved):
        row: dict[str, Any] = {}
        for child in field.children or []:
            child_name = child.name.strip()
            if not child_name:
                continue
            row[child_name] = build_field_template_node(child)
        return [row] if row else [{"value": "verbatim-string"}]

    if is_multi_enum_template_type(resolved):
        values = _clean_enum_values(field.enum_values)
        return [values or ["other"]]

    if is_enum_template_type(resolved):
        return _clean_enum_values(field.enum_values) or ["other"]

    if is_list_template_type(resolved):
        return [list_template_scalar_type(resolved)]

    return template_type_to_nuextract_leaf(resolved)


def build_vlm_template(schema: list[SchemaFieldSpec]) -> dict[str, Any]:
    template: dict[str, Any] = {}
    for field in schema:
        name = field.name.strip()
        if not name:
            continue
        template[name] = build_field_template_node(field)
    return template


def _clean_enum_values(values: list[str] | None) -> list[str]:
    if not values:
        return []
    seen: set[str] = set()
    cleaned: list[str] = []
    for raw in values:
        token = raw.strip()
        if not token or token in seen:
            continue
        seen.add(token)
        cleaned.append(token)
    return cleaned
