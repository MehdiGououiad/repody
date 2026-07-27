from audit_workbench.extraction.types import SchemaFieldSpec
from audit_workbench.extraction.parse import normalize_amount, parse_fields_json, parse_numeric_value
from audit_workbench.extraction.payloads import _fields_payload


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
    assert rows[0].type == "number"
    assert rows[0].confidence == 0.9


def test_parse_fields_json_treats_null_as_missing():
    raw = '{"fields":[{"name":"full_name","value":null},{"name":"id_number","value":"AE230380"}]}'
    schema = [
        SchemaFieldSpec(name="full_name", description="", template_type="string"),
        SchemaFieldSpec(name="id_number", description="", template_type="verbatim-string"),
    ]
    rows = parse_fields_json(raw, schema)
    by_key = {r.key: r for r in rows}
    assert by_key["full_name"].extracted is False
    assert by_key["full_name"].value == "—"
    assert by_key["id_number"].extracted is True
    assert by_key["id_number"].value == "AE230380"


def test_parse_fields_json_preserves_verbatim_with_numeric_looking_name():
    raw = '{"fields":[{"name":"amount_code","value":"6 000,00"}]}'
    schema = [
        SchemaFieldSpec(
            name="amount_code",
            description="",
            template_type="verbatim-string",
        )
    ]
    rows = parse_fields_json(raw, schema)
    assert rows[0].value == "6 000,00"
    assert rows[0].type == "verbatim-string"


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


def test_fields_payload_expands_nested_objects():
    raw = """{
      "document_type": "CNIE",
      "holder_information": {
        "full_name": "Jane Doe",
        "first_name": "Jane",
        "last_name": null
      },
      "document_details": {
        "is_valid": true
      }
    }"""
    schema = [
        SchemaFieldSpec(name="document_type", description="", template_type="string"),
        SchemaFieldSpec(
            name="holder_information",
            description="",
            template_type="object",
            children=[
                SchemaFieldSpec(name="full_name", description="", template_type="string"),
                SchemaFieldSpec(name="first_name", description="", template_type="string"),
                SchemaFieldSpec(name="last_name", description="", template_type="string"),
            ],
        ),
        SchemaFieldSpec(
            name="document_details",
            description="",
            template_type="object",
            children=[
                SchemaFieldSpec(name="is_valid", description="", template_type="boolean"),
            ],
        ),
    ]
    wrapped = _fields_payload(raw, schema)
    fields = parse_fields_json(wrapped, schema)
    by_key = {r.key: r for r in fields}
    assert by_key["document_type"].value == "CNIE"
    assert by_key["holder_information.full_name"].value == "Jane Doe"
    assert by_key["holder_information.last_name"].extracted is False
    assert by_key["document_details.is_valid"].value == "True"


def test_parse_fields_json_expands_nested_object_leaves():
    raw = (
        '{"fields":['
        '{"name":"document_type","value":"CNIE"},'
        '{"name":"holder_information.full_name","value":"Jane Doe"},'
        '{"name":"holder_information.first_name","value":"Jane"},'
        '{"name":"document_details.is_valid","value":"true"}'
        "]}"
    )
    schema = [
        SchemaFieldSpec(name="document_type", description="", template_type="string"),
        SchemaFieldSpec(
            name="holder_information",
            description="",
            template_type="object",
            children=[
                SchemaFieldSpec(name="full_name", description="", template_type="string"),
                SchemaFieldSpec(name="first_name", description="", template_type="string"),
                SchemaFieldSpec(name="last_name", description="", template_type="string"),
            ],
        ),
        SchemaFieldSpec(
            name="document_details",
            description="",
            template_type="object",
            children=[
                SchemaFieldSpec(name="is_valid", description="", template_type="boolean"),
            ],
        ),
    ]
    rows = parse_fields_json(raw, schema)
    by_key = {r.key: r for r in rows}
    assert list(by_key) == [
        "document_type",
        "holder_information.full_name",
        "holder_information.first_name",
        "holder_information.last_name",
        "document_details.is_valid",
    ]
    assert by_key["holder_information.full_name"].value == "Jane Doe"
    assert by_key["holder_information.last_name"].extracted is False
    assert by_key["document_details.is_valid"].value == "true"
