from __future__ import annotations

from audit_workbench.extraction.base import ExtractedFieldResult, SchemaFieldSpec
from audit_workbench.extraction.template_type_inference import resolve_template_type


def _normalize_key(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def _schema_type(field: SchemaFieldSpec) -> str:
    return resolve_template_type(field.name, field.description, field.template_type)


def empty_fields_from_schema(schema: list[SchemaFieldSpec]) -> list[ExtractedFieldResult]:
    """Schema-shaped placeholders when no document is available or nothing was extracted."""
    results: list[ExtractedFieldResult] = []
    for field in schema:
        if not field.name.strip():
            continue
        results.append(
            ExtractedFieldResult(
                key=field.name,
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
    for field in schema:
        if not field.name.strip():
            continue
        norm = _normalize_key(field.name)
        raw = samples.get(field.name) or samples.get(norm) or ""
        value = raw.strip() or "—"
        results.append(
            ExtractedFieldResult(
                key=field.name,
                description=field.description,
                value=value,
                type=_schema_type(field),
                confidence=0.9 if value != "—" else None,
                extracted=value != "—",
            )
        )
    return results
