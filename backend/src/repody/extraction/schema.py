"""Convert workflow schema rows to extraction SchemaFieldSpec."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from repody.extraction.nuextract import (
    is_object_array_template_type,
    is_object_template_type,
    normalize_template_type,
    resolve_template_type,
)
from repody.extraction.types import ExtractedFieldResult, ExtractionIclExample, SchemaFieldSpec
from repody.util.json_shape import normalize_keys_to_snake


def enum_values_from_row(row: dict[str, Any] | None) -> list[str] | None:
    if not row:
        return None
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


def iter_child_rows(raw_children: list[Any] | None) -> Iterator[dict[str, Any]]:
    if not raw_children:
        return
    for row in raw_children:
        if not isinstance(row, dict):
            continue
        yield normalize_keys_to_snake(row)


def children_from_config(config: dict[str, Any] | None) -> list[Any] | None:
    if not isinstance(config, dict):
        return None
    config = normalize_keys_to_snake(config)
    children = config.get("children")
    return children if isinstance(children, list) else None


def field_config_from_parts(
    *,
    enum_values: list[str] | None = None,
    children: list[Any] | None = None,
) -> dict[str, Any] | None:
    config: dict[str, Any] = {}
    if enum_values:
        config["enum_values"] = enum_values
    if children:
        config["children"] = children
    return config or None


def merge_field_row(
    name: str, description: str, template_type: str | None, field_config: dict | None
) -> dict[str, Any]:
    """Flatten snapshot/ORM field into one dict for nested walkers."""
    row: dict[str, Any] = {
        "name": name,
        "description": description or "",
        "template_type": template_type,
    }
    config = normalize_keys_to_snake(field_config or {}) if field_config else {}
    if isinstance(config, dict):
        if config.get("enum_values") is not None:
            row["enum_values"] = config.get("enum_values")
        if config.get("children") is not None:
            row["children"] = config.get("children")
    return row


def _child_specs(raw_children: list[Any] | None) -> list[SchemaFieldSpec] | None:
    children: list[SchemaFieldSpec] = []
    for row in iter_child_rows(raw_children):
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        children.append(
            SchemaFieldSpec(
                name=name,
                description=str(row.get("description") or ""),
                template_type=normalize_template_type(row.get("template_type")),
                enum_values=enum_values_from_row(row),
                children=_child_specs(
                    row.get("children") if isinstance(row.get("children"), list) else None
                ),
            )
        )
    return children or None


def schema_field_spec_from_row(
    *,
    name: str,
    description: str = "",
    template_type: str | None = None,
    field_config: dict[str, Any] | None = None,
    enum_values: list[str] | None = None,
    children: list[Any] | None = None,
) -> SchemaFieldSpec:
    row = merge_field_row(name, description, template_type, field_config)
    if enum_values:
        row["enum_values"] = enum_values
    if children:
        row["children"] = children
    resolved_children = children or children_from_config(field_config)
    return SchemaFieldSpec(
        name=name,
        description=description,
        template_type=normalize_template_type(template_type),
        enum_values=enum_values or enum_values_from_row(row),
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
    children: list[dict[str, Any]] | None = None
    if field.children:
        children = []
        for child in field.children:
            if not child.name.strip():
                continue
            row: dict[str, Any] = {
                "name": child.name,
                "description": child.description,
                "template_type": normalize_template_type(child.template_type),
            }
            if child.enum_values:
                row["enum_values"] = child.enum_values
            nested = field_config_from_spec(child)
            if nested and nested.get("children"):
                row["children"] = nested["children"]
            children.append(row)
    return field_config_from_parts(enum_values=field.enum_values, children=children)


def _schema_type(field: SchemaFieldSpec) -> str:
    return resolve_template_type(field.name, field.description, field.template_type)


def is_nested_object_group(field: SchemaFieldSpec) -> bool:
    """True only for explicit ``object`` groups with children."""
    resolved = resolve_template_type(field.name, field.description, field.template_type)
    if is_object_array_template_type(resolved):
        return False
    return is_object_template_type(resolved) and bool(field.children)


def iter_extraction_leaves(
    schema: list[SchemaFieldSpec],
    *,
    prefix: str = "",
) -> list[tuple[str, SchemaFieldSpec]]:
    """Flatten schema into extraction result leaves.

    Nested ``object`` groups expand to dotted keys (``parent.child``) so UI and
    rules see each leaf. ``object-array`` stays one leaf (JSON table blob).
    """
    leaves: list[tuple[str, SchemaFieldSpec]] = []
    for field in schema:
        name = field.name.strip()
        if not name:
            continue
        key = f"{prefix}.{name}" if prefix else name
        if is_nested_object_group(field):
            leaves.extend(iter_extraction_leaves(field.children or [], prefix=key))
            continue
        leaves.append((key, field))
    return leaves


def empty_fields_from_schema(schema: list[SchemaFieldSpec]) -> list[ExtractedFieldResult]:
    """Schema-shaped placeholders when no document is available or nothing was extracted."""
    results: list[ExtractedFieldResult] = []
    for key, field in iter_extraction_leaves(schema):
        results.append(
            ExtractedFieldResult(
                key=key,
                description=field.description,
                value="—",
                type=_schema_type(field),
                confidence=None,
                extracted=False,
            )
        )
    return results


def fields_from_sample_values(
    schema: list[SchemaFieldSpec],
    samples: dict[str, str],
) -> list[ExtractedFieldResult]:
    """Dry-run / preview: use caller-provided sample values keyed by field name."""
    results: list[ExtractedFieldResult] = []
    for key, field in iter_extraction_leaves(schema):
        raw = samples.get(key) or samples.get(field.name) or ""
        value = raw.strip() or "—"
        results.append(
            ExtractedFieldResult(
                key=key,
                description=field.description,
                value=value,
                type=_schema_type(field),
                confidence=0.9 if value != "—" else None,
                extracted=value != "—",
            )
        )
    return results
