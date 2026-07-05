"""Tests for Run pool classification."""

from __future__ import annotations

from types import SimpleNamespace

from audit_workbench.services.run_pool_classifier import (
    classify_bindings_for_workflow,
    classify_run_documents,
    needs_extract_pool,
)


def test_needs_extract_pool_document_model():
    assert needs_extract_pool("document_model") is True


def test_needs_extract_pool_unknown_modes_default_to_document_model():
    for mode in ("unknown", "obsolete"):
        assert needs_extract_pool(mode) is True


def test_classify_no_bindings_is_fast():
    wf_docs = [SimpleNamespace(id="doc-1", extraction_mode="document_model")]
    assert classify_bindings_for_workflow(wf_docs, None) == "fast"
    assert classify_bindings_for_workflow(wf_docs, []) == "fast"


def test_classify_bindings_with_uploads_is_extract():
    wf_docs = [
        SimpleNamespace(id="doc-1", extraction_mode="document_model"),
    ]
    bindings = [SimpleNamespace(document_id="doc-1")]
    assert classify_bindings_for_workflow(wf_docs, bindings) == "extract"


def test_classify_run_documents_mixed_paths():
    wf_docs = [
        SimpleNamespace(id="doc-1", extraction_mode="document_model"),
        SimpleNamespace(id="doc-2", extraction_mode="document_model"),
    ]
    run_docs = [
        SimpleNamespace(document_id="doc-1", storage_key="k1"),
        SimpleNamespace(document_id="doc-2", storage_key="k2"),
    ]
    assert classify_run_documents(wf_docs, run_docs) == "extract"


def test_classify_run_documents_no_uploads_is_fast():
    wf_docs = [SimpleNamespace(id="doc-1", extraction_mode="document_model")]
    run_docs = [SimpleNamespace(document_id="doc-1", storage_key=None)]
    assert classify_run_documents(wf_docs, run_docs) == "fast"
