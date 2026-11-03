from __future__ import annotations

from repody.app.run.progress import document_wants_extraction
from repody.app.run.snapshot import SnapshotDocument, SnapshotSchemaField


def _doc(**kwargs) -> SnapshotDocument:
    return SnapshotDocument(id="doc-1", document_type="Invoice", position=0, **kwargs)


def test_document_without_schema_or_markdown_is_not_extracted() -> None:
    assert document_wants_extraction(_doc()) is False


def test_markdown_only_document_is_extracted() -> None:
    assert document_wants_extraction(_doc(markdown_extraction=True)) is True


def test_document_with_schema_fields_is_extracted() -> None:
    field = SnapshotSchemaField(id="f1", name="total", description="", position=0)
    assert document_wants_extraction(_doc(schema_fields=[field])) is True
