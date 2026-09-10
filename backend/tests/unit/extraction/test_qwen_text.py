"""Tests for leaf JSON projection and Qwen text prompts."""

from __future__ import annotations

import json

from repody.extraction.fields import fields_from_leaf_json
from repody.extraction.qwen_text import (
    leaf_response_json_schema,
    text_to_json_chat_payload,
)
from repody.extraction.types import SchemaFieldSpec


def test_fields_from_leaf_json_nested_object():
    raw = json.dumps(
        {
            "holder_information": {
                "full_name": "Jane Doe",
                "first_name": "Jane",
            }
        }
    )
    schema = [
        SchemaFieldSpec(
            name="holder_information",
            template_type="object",
            children=[
                SchemaFieldSpec(name="full_name", description="Full name"),
                SchemaFieldSpec(name="first_name", description="First name"),
            ],
        )
    ]
    fields = fields_from_leaf_json(raw, schema)
    by_key = {field.key: field.value for field in fields}
    assert by_key["holder_information.full_name"] == "Jane Doe"
    assert by_key["holder_information.first_name"] == "Jane"


def test_fields_from_leaf_json_flat_dotted_keys():
    raw = json.dumps(
        {
            "address.city": "Casablanca",
            "address.street": "BD ZIRAOUI",
            "national_id": "BE899456",
        }
    )
    schema = [
        SchemaFieldSpec(name="national_id", description="CIN"),
        SchemaFieldSpec(
            name="address",
            template_type="object",
            children=[
                SchemaFieldSpec(name="city", description="City"),
                SchemaFieldSpec(name="street", description="Street"),
            ],
        ),
    ]
    fields = fields_from_leaf_json(raw, schema)
    by_key = {field.key: field.value for field in fields}
    assert by_key["national_id"] == "BE899456"
    assert by_key["address.city"] == "Casablanca"
    assert by_key["address.street"] == "BD ZIRAOUI"


def test_text_to_json_chat_payload_uses_leaf_keys():
    schema = [
        SchemaFieldSpec(name="national_id", description="CIN"),
        SchemaFieldSpec(
            name="address",
            template_type="object",
            children=[
                SchemaFieldSpec(name="city", description="City"),
            ],
        ),
    ]
    payload = text_to_json_chat_payload(
        model="Qwen3.5-4B",
        schema=schema,
        ocr_text="BE899456 CASABLANCA",
        document_type="document",
        extraction_instructions="Copy printed values.",
    )
    system = payload["messages"][0]["content"]
    user = payload["messages"][1]["content"]
    assert '"national_id"' in system
    assert '"address.city"' in system
    assert "address.city" in user
    assert "Copy printed values." in user
    assert "do not invent" in system
    assert "reformat" in system
    assert payload["max_tokens"] >= 256
    assert payload["response_format"]["type"] == "json_schema"
    schema_body = payload["response_format"]["json_schema"]["schema"]
    assert schema_body["properties"]["national_id"]["type"] == "string"
    assert "address.city" in schema_body["properties"]
    assert set(schema_body["required"]) == {"national_id", "address.city"}


def test_leaf_response_json_schema_object_array():
    schema = [
        SchemaFieldSpec(
            name="lines",
            template_type="object-array",
            children=[SchemaFieldSpec(name="qty")],
        )
    ]
    body = leaf_response_json_schema(schema)
    assert body["properties"]["lines"]["type"] == "array"
    assert body["additionalProperties"] is False


def test_text_to_json_chat_payload_can_skip_response_format():
    schema = [SchemaFieldSpec(name="national_id", description="CIN")]
    payload = text_to_json_chat_payload(
        model="Qwen3.5-4B",
        schema=schema,
        ocr_text="BE899456",
        document_type="document",
        use_json_schema=False,
    )
    assert "response_format" not in payload


def test_response_format_unsupported_detects_schema_errors():
    from repody.extraction.qwen_text import _response_format_unsupported

    assert _response_format_unsupported(RuntimeError("response_format type must be json_object"))
    assert not _response_format_unsupported(TimeoutError("timed out"))
