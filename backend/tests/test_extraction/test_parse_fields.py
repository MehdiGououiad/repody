from audit_workbench.extraction.base import SchemaFieldSpec
from audit_workbench.extraction.field_json import normalize_amount, parse_fields_json, parse_numeric_value


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


def test_parse_fields_json_uses_explicit_template_type():
    raw = '{"fields":[{"name":"reference","value":"6 000,00","confidence":0.9}]}'
    schema = [SchemaFieldSpec(name="reference", description="", template_type="verbatim-string")]
    rows = parse_fields_json(raw, schema)
    assert rows[0].value == "6 000,00"
    assert rows[0].type == "verbatim-string"


def test_parse_fields_json_normalizes_explicit_number_type():
    raw = '{"fields":[{"name":"total","value":"6 000,00 EUR","confidence":0.9}]}'
    schema = [SchemaFieldSpec(name="total", description="", template_type="number")]
    rows = parse_fields_json(raw, schema)
    assert rows[0].value == "6000.00"
    assert rows[0].type == "number"


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


def test_parse_fields_preserves_date_template_even_when_name_contains_balance():
    raw = '{"fields":[{"name":"opening_balance_date","value":"2022-02-28","confidence":0.9}]}'
    schema = [
        SchemaFieldSpec(
            name="opening_balance_date",
            description="SOLDE DEPART date",
            template_type="date",
        )
    ]
    rows = parse_fields_json(raw, schema)
    assert rows[0].value == "2022-02-28"
    assert rows[0].type == "date"

    assert parse_numeric_value("PO-2024-991") is None
    assert parse_numeric_value("FAC-42") is None
    assert parse_numeric_value("6000.00") == 6000.0
    assert parse_numeric_value("6 000,00 Dh TTC") == 6000.0
