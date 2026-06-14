from __future__ import annotations

from audit_workbench.extraction.base import ExtractedFieldResult, SchemaFieldSpec


def _normalize_key(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def _field_type(name: str, description: str = "") -> str:
    blob = f"{name} {description}".lower()
    if any(
        token in blob
        for token in ("amount", "price", "cost", "total", "fee", "montant", "balance", "currency")
    ):
        return "currency"
    if "date" in blob or "time" in blob:
        return "date"
    if "percent" in blob or "rate" in blob or "%" in blob:
        return "percent"
    return "string"


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
                type=_field_type(field.name, field.description),
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
                type=_field_type(field.name, field.description),
                confidence=0.9 if value != "—" else None,
                extracted=value != "—",
            )
        )
    return results
