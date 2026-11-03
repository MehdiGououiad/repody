"""Schema leaves: the flat ``parent.child`` keys the UI and rules see."""

from __future__ import annotations

from repody.extraction.types import ExtractedFieldResult, SchemaFieldSpec
from repody.rules.value_coercion import MISSING


def iter_extraction_leaves(
    schema: list[SchemaFieldSpec], *, prefix: str = ""
) -> list[tuple[str, SchemaFieldSpec]]:
    """Flatten the schema: ``object`` groups expand to dotted keys; an ``object-array``
    stays one leaf (its JSON table)."""
    leaves: list[tuple[str, SchemaFieldSpec]] = []
    for field in schema:
        if not field.name:
            continue
        key = f"{prefix}.{field.name}" if prefix else field.name
        if field.template_type == "object" and field.children:
            leaves.extend(iter_extraction_leaves(field.children, prefix=key))
        else:
            leaves.append((key, field))
    return leaves


def _leaf(key: str, field: SchemaFieldSpec, value: str) -> ExtractedFieldResult:
    extracted = value != MISSING
    return ExtractedFieldResult(
        key=key,
        description=field.description,
        value=value,
        type=field.template_type,
        confidence=0.9 if extracted else None,
        extracted=extracted,
    )


def empty_fields_from_schema(schema: list[SchemaFieldSpec]) -> list[ExtractedFieldResult]:
    """Schema-shaped placeholders when there is no document or nothing was extracted."""
    return [_leaf(key, field, MISSING) for key, field in iter_extraction_leaves(schema)]


def fields_from_sample_values(
    schema: list[SchemaFieldSpec], samples: dict[str, str]
) -> list[ExtractedFieldResult]:
    """Dry run: caller-provided sample values keyed by leaf key or field name."""
    return [
        _leaf(key, field, (samples.get(key) or samples.get(field.name) or "").strip() or MISSING)
        for key, field in iter_extraction_leaves(schema)
    ]
