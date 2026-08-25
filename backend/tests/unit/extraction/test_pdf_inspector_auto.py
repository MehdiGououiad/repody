"""Unit tests for Automode pdf-inspector quality gate and pipeline routing."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from repody.extraction.pdf_inspector_auto import (
    PdfInspection,
    mime_is_pdf,
    native_quality_ok,
)
from repody.extraction.pipeline import extract_document
from repody.extraction.types import ExtractedFieldResult, ExtractionResult, SchemaFieldSpec


def _inspection(**overrides) -> PdfInspection:
    base = dict(
        pdf_type="text_based",
        confidence=0.95,
        page_count=2,
        markdown="# Invoice\n\nTotal: 100 EUR\nVendor: Acme Corp\n",
        pages_needing_ocr=(),
        has_encoding_issues=False,
        available=True,
        error=None,
    )
    base.update(overrides)
    return PdfInspection(**base)


def test_mime_is_pdf_by_header_and_mime():
    assert mime_is_pdf("application/pdf", b"%PDF-1.4")
    assert mime_is_pdf("application/octet-stream", b"%PDF-1.7")
    assert not mime_is_pdf("image/png", b"\x89PNG\r\n\x1a\n")


def test_native_quality_ok_accepts_text_based():
    ok, reason = native_quality_ok(_inspection(), min_confidence=0.7, min_chars=40)
    assert ok is True
    assert reason == ""


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"pdf_type": "scanned"}, "pdf_type:scanned"),
        ({"pdf_type": "mixed"}, "pdf_type:mixed"),
        ({"confidence": 0.2}, "low_confidence"),
        ({"has_encoding_issues": True}, "encoding_issues"),
        ({"pages_needing_ocr": (1,)}, "pages_needing_ocr"),
        ({"markdown": None}, "empty_markdown"),
        ({"markdown": "short"}, "short_markdown"),
        (
            {
                "available": False,
                "error": "pdf-inspector not installed",
                "pdf_type": "unknown",
            },
            "pdf-inspector not installed",
        ),
    ],
)
def test_native_quality_gate_rejects(overrides, expected):
    ok, reason = native_quality_ok(
        _inspection(**overrides),
        min_confidence=0.7,
        min_chars=40,
    )
    assert ok is False
    assert reason == expected


@pytest.fixture
def pipeline_mocks(monkeypatch):
    fallback = ExtractionResult(
        fields=[
            ExtractedFieldResult(
                key="total",
                description="",
                value="from-fallback",
                type="string",
                confidence=0.9,
                extracted=True,
            )
        ],
        raw_text="fallback",
    )
    native = ExtractionResult(
        fields=[
            ExtractedFieldResult(
                key="total",
                description="",
                value="from-native",
                type="string",
                confidence=0.9,
                extracted=True,
            )
        ],
        raw_text="native",
        markdown_text="# Invoice",
    )
    monkeypatch.setattr(
        "repody.extraction.pipeline.extract_with_document_model",
        AsyncMock(return_value=fallback),
    )
    monkeypatch.setattr(
        "repody.extraction.pipeline.get_cached",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "repody.extraction.pipeline.set_cached",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "repody.extraction.pipeline.extract_via_native_markdown",
        AsyncMock(return_value=native),
    )
    return {"fallback": fallback, "native": native}


@pytest.mark.asyncio
async def test_auto_accepts_native_path(pipeline_mocks, monkeypatch):
    monkeypatch.setattr(
        "repody.extraction.pipeline.inspect_pdf_bytes",
        MagicMock(return_value=_inspection()),
    )
    result = await extract_document(
        b"%PDF-1.4 fake",
        "application/pdf",
        "Invoice",
        [SchemaFieldSpec(name="total", description="Total")],
        document_model_id="paddleocr:qwen",
        native_pdf_auto=True,
    )
    assert result.fields[0].value == "from-native"
    assert result.meta is not None
    assert result.meta.native_pdf is not None
    assert result.meta.native_pdf["source"] == "pdf_inspector"


@pytest.mark.asyncio
async def test_auto_falls_back_for_scanned(pipeline_mocks, monkeypatch):
    monkeypatch.setattr(
        "repody.extraction.pipeline.inspect_pdf_bytes",
        MagicMock(return_value=_inspection(pdf_type="scanned", markdown=None)),
    )
    result = await extract_document(
        b"%PDF-1.4 fake",
        "application/pdf",
        "Invoice",
        [SchemaFieldSpec(name="total", description="Total")],
        document_model_id="paddleocr:qwen",
        native_pdf_auto=True,
    )
    assert result.fields[0].value == "from-fallback"
    assert result.meta is not None
    assert result.meta.native_pdf["source"] == "fallback"
    assert "pdf_type:scanned" in result.meta.native_pdf["fallbackReason"]


@pytest.mark.asyncio
async def test_auto_skips_non_pdf(pipeline_mocks, monkeypatch):
    inspect = MagicMock()
    monkeypatch.setattr("repody.extraction.pipeline.inspect_pdf_bytes", inspect)
    result = await extract_document(
        b"\x89PNG\r\n\x1a\n",
        "image/png",
        "ID",
        [SchemaFieldSpec(name="total", description="Total")],
        document_model_id="paddleocr:qwen",
        native_pdf_auto=True,
    )
    inspect.assert_not_called()
    assert result.fields[0].value == "from-fallback"
    assert result.meta.native_pdf["fallbackReason"] == "not_pdf"


@pytest.mark.asyncio
async def test_auto_off_never_inspects(pipeline_mocks, monkeypatch):
    inspect = MagicMock()
    monkeypatch.setattr("repody.extraction.pipeline.inspect_pdf_bytes", inspect)
    result = await extract_document(
        b"%PDF-1.4 fake",
        "application/pdf",
        "Invoice",
        [SchemaFieldSpec(name="total", description="Total")],
        document_model_id="paddleocr:qwen",
        native_pdf_auto=False,
    )
    inspect.assert_not_called()
    assert result.fields[0].value == "from-fallback"
    assert result.meta.native_pdf is None
