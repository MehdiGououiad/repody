from __future__ import annotations

from repody.extraction.cache import (
    CACHE_VERSION,
    cache_key,
    schema_fingerprint,
    should_cache_result,
)
from repody.extraction.fields import fields_from_nuextract_json
from repody.extraction.schema import empty_fields_from_schema
from repody.extraction.types import ExtractedFieldResult, ExtractionResult, SchemaFieldSpec


def test_empty_schema_fields_have_no_fake_values():
    schema = [SchemaFieldSpec(name="total_amount", description="Total TTC")]
    fields = empty_fields_from_schema(schema)
    assert len(fields) == 1
    assert fields[0].value == "—"
    assert fields[0].extracted is False


def test_fields_from_nuextract_json_uses_schema_names():
    schema = [
        SchemaFieldSpec(name="contract_id", description="Contract ID"),
        SchemaFieldSpec(name="annual_fee", description="Annual Fee"),
    ]
    raw = '{"contract_id":"ABC-991","annual_fee":"12 500,00"}'
    fields = fields_from_nuextract_json(raw, schema)
    by_key = {f.key: f for f in fields}
    assert by_key["contract_id"].extracted is True
    assert by_key["contract_id"].value == "ABC-991"
    assert by_key["annual_fee"].extracted is True
    assert by_key["annual_fee"].value == "12 500,00"


def test_should_not_cache_empty_extractions():
    no_text = ExtractionResult(
        fields=[
            ExtractedFieldResult(
                key="x", description="", value="—", type="string", confidence=None, extracted=False
            )
        ],
        raw_text=None,
        markdown_text=None,
    )
    text_only = ExtractionResult(
        fields=[
            ExtractedFieldResult(
                key="x", description="", value="—", type="string", confidence=None, extracted=False
            )
        ],
        markdown_text="## Page 1\n\nInvoice total 6000",
    )
    good = ExtractionResult(
        fields=[
            ExtractedFieldResult(
                key="x", description="", value="1", type="string", confidence=0.9, extracted=True
            )
        ],
        raw_text="some text",
    )
    assert should_cache_result(no_text) is False
    assert should_cache_result(text_only) is True
    assert should_cache_result(good) is True


def _key(**overrides) -> str:
    args = {
        "content_hash": "abc123",
        "schema": [SchemaFieldSpec(name="total", description="Total")],
        "served_model": "nuextract3-q4_k_m",
        "markdown_extraction": False,
        "extraction_instructions": "",
        "icl_examples": None,
    }
    return cache_key(**{**args, **overrides})


def test_cache_key_changes_with_content_model_and_request():
    base = _key()
    assert base.startswith(f"extract:{CACHE_VERSION}:")
    assert base.endswith(":abc123")
    assert _key(content_hash="def456") != base
    assert _key(served_model="other-model") != base
    assert _key(markdown_extraction=True) != base
    assert _key(extraction_instructions="Dates are DD/MM/YYYY") != base
    assert _key() == base


def test_schema_fingerprint_includes_descriptions():
    same_names = [
        SchemaFieldSpec(name="total_amount", description="Total TTC"),
        SchemaFieldSpec(name="invoice_number", description="Invoice reference"),
    ]
    renamed_prompt = [
        SchemaFieldSpec(name="total_amount", description="Montant total TTC incluant taxes"),
        SchemaFieldSpec(name="invoice_number", description="Invoice reference"),
    ]
    assert schema_fingerprint(same_names) != schema_fingerprint(renamed_prompt)


def test_schema_fingerprint_includes_template_type():
    as_text = [
        SchemaFieldSpec(name="total_amount", description="Total", template_type="verbatim-string")
    ]
    as_number = [SchemaFieldSpec(name="total_amount", description="Total", template_type="number")]
    assert schema_fingerprint(as_text) != schema_fingerprint(as_number)


def test_schema_fingerprint_stable_for_identical_schema():
    schema = [
        SchemaFieldSpec(name="total_amount", description="Total TTC"),
        SchemaFieldSpec(name="invoice_number", description="Invoice reference"),
    ]
    assert schema_fingerprint(schema) == schema_fingerprint(list(schema))
