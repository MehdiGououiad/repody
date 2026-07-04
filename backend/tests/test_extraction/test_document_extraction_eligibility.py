from __future__ import annotations

from audit_workbench.extraction.document_modes import (
    document_has_schema_fields,
    document_needs_extraction,
)
from audit_workbench.services.run.snapshot import SnapshotDocument, SnapshotSchemaField


def test_document_has_schema_fields_false_when_empty() -> None:
    doc = SnapshotDocument(
        id="doc-1",
        document_type="Invoice",
        position=0,
        extraction_mode="document_model",
        validation_mode="logic_only",
        ocr_model="repody:vlm",
        schema_fields=[],
    )
    assert document_has_schema_fields(doc) is False


def test_document_needs_extraction_with_markdown_only() -> None:
    doc = SnapshotDocument(
        id="doc-1",
        document_type="Document",
        position=0,
        extraction_mode="document_model",
        validation_mode="logic_only",
        ocr_model="repody:vlm",
        markdown_extraction=True,
        schema_fields=[],
    )
    assert document_needs_extraction(doc, has_file=True) is True


def test_document_needs_extraction_false_without_file_or_trigger() -> None:
    doc = SnapshotDocument(
        id="doc-1",
        document_type="Document",
        position=0,
        extraction_mode="document_model",
        validation_mode="logic_only",
        ocr_model="repody:vlm",
        schema_fields=[],
    )
    assert document_needs_extraction(doc, has_file=False) is False
    assert document_needs_extraction(doc, has_file=True) is False
