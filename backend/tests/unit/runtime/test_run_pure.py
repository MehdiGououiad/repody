"""Unit tests for platform run pure helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from repody.runtime.run.ids import document_row_id, new_id, new_run_id


def test_new_run_id_prefixes() -> None:
    fixed = datetime(2026, 1, 1, tzinfo=UTC)
    api_id = new_run_id("api", now=lambda: fixed, uuid_hex=lambda: "abcd1234")
    test_id = new_run_id("test", now=lambda: fixed, uuid_hex=lambda: "abcd1234")
    assert api_id.startswith("AUD-")
    assert test_id.startswith("AUD-TEST-")
    assert api_id.endswith("abcd1234")


def test_document_row_id() -> None:
    assert document_row_id(uuid_hex=lambda: "xyz") == "rdoc-xyz"


def test_new_id_prefix() -> None:
    assert new_id("fld", uuid_hex=lambda: "abc") == "fld-abc"
