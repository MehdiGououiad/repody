from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from repody.extraction.types import ExtractedFieldResult, ExtractionResult, SchemaFieldSpec
from repody.extraction.pipeline import extract_document


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
        "repody.extraction.pipeline.extract_with_document_model",
        AsyncMock(side_effect=fake_extract),
    )
    monkeypatch.setattr(
        "repody.extraction.pipeline.get_cached",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "repody.extraction.pipeline.set_cached",
        AsyncMock(),
    )


@pytest.mark.asyncio
async def test_document_model_path_returns_fields(mock_document_model):
    pdf = Path(__file__).resolve().parents[3] / "e2e" / "fixtures" / "documents" / "Facture.pdf"
    if not pdf.is_file():
        pytest.skip("Facture.pdf fixture missing")

    schema = [SchemaFieldSpec(name="total_amount", description="TTC")]
    result = await extract_document(
        pdf.read_bytes(),
        "application/pdf",
        "Invoice",
        schema,
        extraction_mode="document_model",
        document_model_id="repody:vlm",
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
            markdown_text="## Page 1\n\nHello",
        )

    monkeypatch.setattr(
        "repody.extraction.pipeline.extract_with_document_model",
        AsyncMock(side_effect=fake_extract),
    )
    monkeypatch.setattr(
        "repody.extraction.pipeline.get_cached",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "repody.extraction.pipeline.set_cached",
        AsyncMock(),
    )

    result = await extract_document(
        b"%PDF-1.4\n%%EOF",
        "application/pdf",
        "Document",
        [],
        extraction_mode="document_model",
        document_model_id="repody:vlm",
        markdown_extraction=True,
    )
    assert result.markdown_text == "## Page 1\n\nHello"
