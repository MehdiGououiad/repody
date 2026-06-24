from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from audit_workbench.extraction.base import ExtractedFieldResult, ExtractionResult, SchemaFieldSpec
from audit_workbench.extraction.pipeline import PipelineExtractor


@pytest.fixture
def mock_document_model(monkeypatch):
    async def fake_extract(*_args, **_kwargs):
        return ExtractionResult(
            fields=[
                ExtractedFieldResult(
                    key="total_amount",
                    description="TTC",
                    value="6000.00",
                    type="currency",
                    confidence=0.95,
                    extracted=True,
                )
            ],
            raw_text="Total TTC 6000.00",
        )

    monkeypatch.setattr(
        "audit_workbench.extraction.pipeline.extract_with_document_model",
        AsyncMock(side_effect=fake_extract),
    )
    monkeypatch.setattr(
        "audit_workbench.extraction.pipeline.get_cached",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "audit_workbench.extraction.pipeline.set_cached",
        AsyncMock(),
    )


@pytest.mark.asyncio
async def test_document_model_path_returns_fields(mock_document_model):
    pdf = Path(__file__).resolve().parents[3] / "e2e" / "fixtures" / "documents" / "Facture.pdf"
    if not pdf.is_file():
        pytest.skip("Facture.pdf fixture missing")

    extractor = PipelineExtractor()
    schema = [SchemaFieldSpec(name="total_amount", description="TTC")]
    result = await extractor.extract(
        pdf.read_bytes(),
        "application/pdf",
        "Invoice",
        schema,
        extraction_mode="document_model",
        ocr_model="repody:vlm",
    )
    assert result.raw_text is not None
    assert any(f.key == "total_amount" and f.value == "6000.00" for f in result.fields)


@pytest.mark.asyncio
async def test_markdown_extraction_runs_without_schema_fields(monkeypatch):
    async def fake_extract(*_args, **kwargs):
        assert kwargs.get("markdown_extraction") is True
        return ExtractionResult(
            fields=[],
            raw_text=None,
            ocr_text="## Page 1\n\nHello",
        )

    monkeypatch.setattr(
        "audit_workbench.extraction.pipeline.extract_with_document_model",
        AsyncMock(side_effect=fake_extract),
    )
    monkeypatch.setattr(
        "audit_workbench.extraction.pipeline.get_cached",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "audit_workbench.extraction.pipeline.set_cached",
        AsyncMock(),
    )

    extractor = PipelineExtractor()
    result = await extractor.extract(
        b"%PDF-1.4\n%%EOF",
        "application/pdf",
        "Document",
        [],
        extraction_mode="document_model",
        ocr_model="repody:vlm",
        markdown_extraction=True,
    )
    assert result.ocr_text == "## Page 1\n\nHello"
