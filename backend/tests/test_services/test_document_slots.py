import pytest

from audit_workbench.services.document_slots import resolve_document_slot_keys


class _Doc:
    def __init__(self, id: str, document_type: str) -> None:
        self.id = id
        self.document_type = document_type


def test_resolve_by_document_type_name_case_insensitive():
    docs = [_Doc("doc-abc", "Facture")]
    assert resolve_document_slot_keys(docs, ["facture"]) == ["doc-abc"]


def test_resolve_by_internal_id():
    docs = [_Doc("doc-abc", "Facture")]
    assert resolve_document_slot_keys(docs, ["doc-abc"]) == ["doc-abc"]


def test_resolve_unknown_slot_raises():
    docs = [_Doc("doc-abc", "Facture")]
    with pytest.raises(ValueError, match="Unknown document slot"):
        resolve_document_slot_keys(docs, ["Invoice"])


def test_resolve_ambiguous_type_raises():
    docs = [_Doc("doc-a", "Invoice"), _Doc("doc-b", "invoice")]
    with pytest.raises(ValueError, match="Ambiguous document type"):
        resolve_document_slot_keys(docs, ["Invoice"])
