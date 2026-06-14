import pytest

from audit_workbench.extraction.base import SchemaFieldSpec
from audit_workbench.extraction.parse_fields import (
    VLM_OCR_PROMPT,
    build_extraction_prompt,
    build_extraction_user_message,
    looks_like_prompt_echo,
    normalize_amount,
    parse_fields_json,
)


def test_parse_fields_json():
    raw = '{"fields":[{"name":"line_total","value":"5625.00","confidence":0.95}]}'
    schema = [SchemaFieldSpec(name="line_total", description="Line total amount")]
    rows = parse_fields_json(raw, schema)
    assert rows[0].value == "5625.00"
    assert rows[0].extracted is True


def test_parse_fields_json_normalizes_amounts():
    raw = '{"fields":[{"name":"grand_total","value":"6 000,00","confidence":0.9}]}'
    schema = [SchemaFieldSpec(name="grand_total", description="Grand total")]
    rows = parse_fields_json(raw, schema)
    assert rows[0].value == "6000.00"


def test_build_prompt_lists_fields_and_descriptions():
    schema = [
        SchemaFieldSpec(name="reference_id", description="Document reference number"),
        SchemaFieldSpec(name="grand_total", description="Grand total amount"),
    ]
    prompt = build_extraction_prompt(schema, "Contract")
    assert "reference_id" in prompt
    assert "Document reference number" in prompt
    assert "grand_total" in prompt
    assert "Return JSON only" in prompt


def test_build_extraction_user_message_includes_document_text():
    schema = [SchemaFieldSpec(name="total_amount", description="Total TTC")]
    msg = build_extraction_user_message("Total TTC 6000,00", schema, "Invoice", max_chars=1000)
    assert "--- DOCUMENT TEXT ---" in msg
    assert "6000,00" in msg


def test_normalize_amount_locale():
    assert normalize_amount("6 000,00") == "6000.00"
    assert normalize_amount("5 000,00") == "5000.00"


def test_normalize_amount_strips_ocr_currency_suffix():
    assert normalize_amount("6000.00DhTTC") == "6000.00"
    assert normalize_amount("1 234,56 EUR") == "1234.56"


def test_parse_fields_preserves_identifier_containing_number():
    raw = '{"fields":[{"name":"invoice_number","value":"FAC-42","confidence":0.9}]}'
    schema = [SchemaFieldSpec(name="invoice_number", description="Invoice reference number")]
    rows = parse_fields_json(raw, schema)
    assert rows[0].value == "FAC-42"


def test_heuristic_extracts_total_from_invoice_text():
    from audit_workbench.extraction.base import SchemaFieldSpec
    from audit_workbench.extraction.parse_fields import extract_fields_heuristic

    text = "Facture\nTotal TTC 6000.00 DhTTC\nMontant HT 5000.00"
    schema = [SchemaFieldSpec(name="total_amount", description="Montant total TTC")]
    rows = extract_fields_heuristic(text, schema)
    assert rows is not None
    assert rows[0].value == "6000.00"
    assert rows[0].extracted is True


@pytest.mark.asyncio
async def test_heuristic_extraction_does_not_call_inference():
    from audit_workbench.extraction.parse_fields import extract_fields_heuristic

    text = "Facture\nTotal TTC 6000.00 DhTTC"
    schema = [SchemaFieldSpec(name="total_amount", description="Montant total TTC")]
    rows = extract_fields_heuristic(text, schema)
    assert rows is not None
    assert rows[0].value == "6000.00"


def test_extraction_num_ctx_sizes_to_prompt():
    from audit_workbench.extraction.parse_fields import extraction_num_ctx

    assert extraction_num_ctx(900, max_tokens=128, cap=1024) == 512
    assert extraction_num_ctx(6000, max_tokens=128, cap=1024) == 1024


def test_vlm_ocr_prompt_is_empty():
    assert VLM_OCR_PROMPT == ""


def test_looks_like_prompt_echo():
    schema = [SchemaFieldSpec(name=f"field_{i}", description=f"Field {i}") for i in range(6)]
    echo = build_extraction_prompt(schema, "Form")
    assert looks_like_prompt_echo(echo) is True
    assert looks_like_prompt_echo("Reference: ABC-123\nTotal: 6000,00") is False
