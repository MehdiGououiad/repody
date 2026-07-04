from __future__ import annotations

from audit_workbench.extraction.base import (
    DocumentExtractor,
    ExtractionResult,
    SchemaFieldSpec,
)
from audit_workbench.extraction.schema_fields import empty_fields_from_schema


def extract_document_fields(
    schema: list[dict],
    *,
    sample_values: dict[str, str] | None = None,
) -> list:
    """Sync helper for dry-run callers — never injects hardcoded demo data."""
    from audit_workbench.extraction.schema_fields import fields_from_sample_values

    specs = [
        SchemaFieldSpec(
            name=(f.get("name") or "").strip(),
            description=f.get("description") or "",
            template_type=f.get("templateType") or f.get("template_type"),
        )
        for f in schema
        if (f.get("name") or "").strip()
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
        extraction_mode: str = "auto",
        ocr_model: str | None = None,
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
            ocr_model,
            storage_key,
            file_size,
            bundle,
            kwargs,
        )
        return ExtractionResult(fields=empty_fields_from_schema(schema))
