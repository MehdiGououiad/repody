from __future__ import annotations

from audit_workbench.extraction.base import (
    DocumentExtractor,
    ExtractionResult,
    SchemaFieldSpec,
)
from audit_workbench.extraction.document_modes import DEFAULT_READ_PATH_ID
from audit_workbench.extraction.schema_fields import empty_fields_from_schema, fields_from_sample_values
from audit_workbench.util.json_shape import normalize_keys_to_snake


def extract_document_fields(
    schema: list[dict],
    *,
    sample_values: dict[str, str] | None = None,
) -> list:
    """Sync helper for dry-run callers — never injects hardcoded demo data."""
    specs = [
        SchemaFieldSpec(
            name=(row.get("name") or "").strip(),
            description=row.get("description") or "",
            template_type=row.get("template_type"),
        )
        for f in schema
        for row in [normalize_keys_to_snake(f) if isinstance(f, dict) else f]
        if isinstance(row, dict) and (row.get("name") or "").strip()
    ]
    if sample_values:
        return fields_from_sample_values(specs, sample_values)
    return empty_fields_from_schema(specs)


class StubDocumentExtractor(DocumentExtractor):
    """Returns schema placeholders only (no fake document values)."""

    async def extract(
        self,
        document_bytes: bytes | None,
        mime_type: str,
        document_type: str,
        schema: list[SchemaFieldSpec],
        *,
        extraction_mode: str = DEFAULT_READ_PATH_ID,
        document_model_id: str | None = None,
        storage_key: str | None = None,
        file_size: int | None = None,
        bundle: object | None = None,
        **kwargs: object,
    ) -> ExtractionResult:
        _ = (
            document_bytes,
            mime_type,
            document_type,
            extraction_mode,
            document_model_id,
            storage_key,
            file_size,
            bundle,
            kwargs,
        )
        return ExtractionResult(fields=empty_fields_from_schema(schema))
