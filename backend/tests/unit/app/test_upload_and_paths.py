from __future__ import annotations

import pytest

from audit_workbench.extraction.types import ExtractedFieldResult, SchemaFieldSpec
from audit_workbench.extraction.modes import parse_read_path
from audit_workbench.rules.rule_syntax import validate_llm_rule_body, validate_logic_rule_body
from audit_workbench.app.uploads.validation import UploadValidationError, validate_upload_file
from audit_workbench.settings import Settings
from audit_workbench.infra.storage.mime import resolve_mime, sanitize_filename, sniff_mime


def test_default_read_path_is_document_model():
    assert parse_read_path(None).id == "document_model"
    assert parse_read_path(None).read == "document_model"


def test_sniff_pdf_and_resolve_mime():
    data = b"%PDF-1.4 fake"
    assert sniff_mime(data) == "application/pdf"
    assert resolve_mime(data=data, declared="text/plain") == "application/pdf"


def test_sanitize_filename_strips_traversal():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert "/" not in sanitize_filename("foo/bar/baz.pdf")


def test_upload_rejects_oversized_file():
    settings = Settings(max_upload_bytes=10)
    with pytest.raises(UploadValidationError):
        validate_upload_file(
            filename="big.pdf",
            declared_mime="application/pdf",
            data=b"%PDF-" + b"x" * 20,
            settings=settings,
        )


def test_upload_rejects_disallowed_mime():
    settings = Settings()
    with pytest.raises(UploadValidationError):
        validate_upload_file(
            filename="doc.txt",
            declared_mime="text/plain",
            data=b"hello world",
            settings=settings,
        )


def test_upload_rejects_declared_pdf_with_non_pdf_content():
    settings = Settings()
    with pytest.raises(UploadValidationError):
        validate_upload_file(
            filename="fake.pdf",
            declared_mime="application/pdf",
            data=b"not a real pdf at all",
            settings=settings,
        )


def test_upload_accepts_pdf_bytes_with_generic_declared_mime():
    settings = Settings()
    _safe_name, verified_mime = validate_upload_file(
        filename="doc.bin",
        declared_mime="application/octet-stream",
        data=b"%PDF-1.4 fake",
        settings=settings,
    )
    assert verified_mime == "application/pdf"


def test_confirm_accepts_octet_stream_when_sniffed_png():
    from audit_workbench.infra.storage.mime import mimes_match_for_confirm

    assert mimes_match_for_confirm(
        prepared="application/octet-stream",
        verified="image/png",
    )
    assert mimes_match_for_confirm(prepared="image/png", verified="image/png")
    assert mimes_match_for_confirm(prepared="image/jpg", verified="image/jpeg")
    # JPEG bytes named .png (Gououiad CNIE fixtures) — sniff wins
    assert mimes_match_for_confirm(prepared="image/png", verified="image/jpeg")
    assert mimes_match_for_confirm(prepared="image/jpeg", verified="image/png")
    # Prepared PDF + sniffed image: content wins (allow-list already enforced)
    assert mimes_match_for_confirm(prepared="application/pdf", verified="image/png")
    # Unsniffable content still matches equality; validate_upload_file rejects later
    assert mimes_match_for_confirm(
        prepared="application/octet-stream",
        verified="application/octet-stream",
    )
    assert not mimes_match_for_confirm(
        prepared="application/pdf",
        verified="application/octet-stream",
    )


def test_gououiad_cnie_fixtures_are_jpeg_despite_png_extension():
    from pathlib import Path

    from audit_workbench.infra.storage.mime import JPEG, sniff_mime

    root = Path(__file__).resolve().parents[4] / "e2e" / "fixtures" / "documents"
    for name in ("gououiad-cnie-front.png", "gououiad-cnie-back.png"):
        data = (root / name).read_bytes()
        assert sniff_mime(data) == JPEG, name


def test_validate_logic_rule_body():
    assert validate_logic_rule_body("subtotal + tax == total_amount") is None
    assert validate_logic_rule_body("") is not None


def test_validate_llm_rule_body():
    assert validate_llm_rule_body("Check total matches PO.") is None
    assert validate_llm_rule_body("") is not None


def test_field_coverage_ratio():
    schema = [SchemaFieldSpec(name="total_amount", description="Total TTC")]
    fields = [
        ExtractedFieldResult(
            key="total_amount",
            description="",
            value="6000.00",
            type="currency",
            confidence=0.9,
            extracted=True,
        )
    ]
    extracted = sum(1 for f in fields if f.extracted)
    assert extracted / len(schema) == 1.0
