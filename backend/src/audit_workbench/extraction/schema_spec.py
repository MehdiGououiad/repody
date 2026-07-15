"""Convert workflow schema rows to extraction SchemaFieldSpec."""

from __future__ import annotations

from typing import Any

from audit_workbench.extraction.base import ExtractionIclExample, SchemaFieldSpec
from audit_workbench.extraction.nuextract_types import normalize_template_type
from audit_workbench.util.json_shape import normalize_keys_to_snake


def _child_specs(raw_children: list[Any] | None) -> list[SchemaFieldSpec] | None:
    if not raw_children:
        return None
    children: list[SchemaFieldSpec] = []
    for row in raw_children:
        if not isinstance(row, dict):
            continue
        row = normalize_keys_to_snake(row)
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        children.append(
            SchemaFieldSpec(
                name=name,
                description=str(row.get("description") or ""),
                template_type=normalize_template_type(row.get("template_type")),
                enum_values=_enum_values(row),
                children=_child_specs(row.get("children")),
            )
        )
    return children or None


def _enum_values(row: dict[str, Any]) -> list[str] | None:
    row = normalize_keys_to_snake(row)
    raw = row.get("enum_values")
    if not isinstance(raw, list):
        config = row.get("field_config")
        if isinstance(config, dict):
            config = normalize_keys_to_snake(config)
            raw = config.get("enum_values")
    if not isinstance(raw, list):
        return None
    values = [str(item).strip() for item in raw if str(item).strip()]
    return values or None


def schema_field_spec_from_row(
    *,
    name: str,
    description: str = "",
    template_type: str | None = None,
    field_config: dict[str, Any] | None = None,
    enum_values: list[str] | None = None,
    children: list[Any] | None = None,
) -> SchemaFieldSpec:
    config = normalize_keys_to_snake(field_config or {})
    resolved_enum = enum_values or _enum_values({"enum_values": config.get("enum_values")})
    resolved_children = children or config.get("children")
    return SchemaFieldSpec(
        name=name,
        description=description,
        template_type=normalize_template_type(template_type),
        enum_values=resolved_enum,
        children=_child_specs(resolved_children if isinstance(resolved_children, list) else None),
    )


def schema_field_spec_from_orm(field: Any) -> SchemaFieldSpec:
    config = getattr(field, "field_config", None) or {}
    return schema_field_spec_from_row(
        name=field.name,
        description=field.description or "",
        template_type=getattr(field, "template_type", None),
        field_config=config if isinstance(config, dict) else {},
    )


def schema_specs_from_document(doc: Any) -> list[SchemaFieldSpec]:
    fields = sorted(getattr(doc, "schema_fields", None) or [], key=lambda item: item.position)
    specs: list[SchemaFieldSpec] = []
    for field in fields:
        if not field.name.strip():
            continue
        specs.append(schema_field_spec_from_orm(field))
    return specs


def icl_examples_from_document(doc: Any) -> list[ExtractionIclExample]:
    raw = getattr(doc, "extraction_icl_examples", None)
    if raw is None and isinstance(doc, dict):
        doc = normalize_keys_to_snake(doc)
        raw = doc.get("extraction_icl_examples")
    if not isinstance(raw, list):
        return []
    examples: list[ExtractionIclExample] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        input_text = str(row.get("input") or "").strip()
        output_text = str(row.get("output") or "").strip()
        if input_text and output_text:
            examples.append(ExtractionIclExample(input=input_text, output=output_text))
    return examples


def field_config_from_spec(field: SchemaFieldSpec) -> dict[str, Any] | None:
    config: dict[str, Any] = {}
    if field.enum_values:
        config["enum_values"] = field.enum_values
    if field.children:
        config["children"] = [
            {
                "name": child.name,
                "description": child.description,
                "template_type": normalize_template_type(child.template_type),
                **(
                    {"enum_values": child.enum_values}
                    if child.enum_values
                    else {}
                ),
            }
            for child in field.children
            if child.name.strip()
        ]
    return config or None
