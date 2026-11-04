import json

import pymupdf
import pytest

from repody.extraction.fields import leaf_values
from repody.extraction.nuextract import instructions, markdown_request, structured_request, template
from repody.extraction.render import page_images
from repody.rules.values import MISSING
from repody.schemas.workflow import DocumentDef, IclExample, SchemaField

FIELDS = [
    SchemaField(name="total", description="Amount due", template_type="number"),
    SchemaField(name="currency", template_type="enum", enum_values=["MAD", "EUR"]),
    SchemaField(name="tags", template_type="string-list"),
    SchemaField(
        name="vendor",
        template_type="object",
        children=[SchemaField(name="name", description="Legal name")],
    ),
    SchemaField(
        name="lines",
        template_type="object-array",
        children=[SchemaField(name="label"), SchemaField(name="amount", template_type="number")],
    ),
]


def test_template_follows_nuextract_types():
    assert template(FIELDS) == {
        "total": "number",
        "currency": ["MAD", "EUR"],
        "tags": ["string"],
        "vendor": {"name": "verbatim-string"},
        "lines": [{"label": "verbatim-string", "amount": "number"}],
    }


def test_enum_needs_two_choices():
    with pytest.raises(ValueError, match="at least 2 choices"):
        template([SchemaField(name="kind", template_type="enum", enum_values=["only"])])


def test_structured_request():
    doc = DocumentDef(
        id="d",
        schema=FIELDS,
        extraction_instructions="French invoice.",
        extraction_icl_examples=[IclExample(input="Total 5", output='{"total": 5}')],
    )
    request = structured_request(doc, "nuextract")
    assert request["temperature"] == 0.0  # in-context examples
    assert request["messages"][0]["role"] == "developer"
    assert request["messages"][-1] == {"role": "user", "content": []}
    kwargs = request["chat_template_kwargs"]
    assert json.loads(kwargs["template"])["total"] == "number"
    assert kwargs["instructions"] == (
        "French invoice.\n\nField guidance:\n- total: Amount due\n- vendor.name: Legal name"
    )
    assert instructions(DocumentDef(id="d")) == ""
    assert markdown_request("m")["chat_template_kwargs"]["mode"] == "markdown"


def test_leaf_values():
    answer = json.dumps(
        {"total": 6000, "currency": "MAD", "vendor": {"name": " Acme "}, "lines": [{"label": "x"}]}
    )
    values = {v.key: v for v in leaf_values(FIELDS, answer)}
    assert values["total"].value == "6000"
    assert values["vendor.name"].value == "Acme"
    assert json.loads(values["lines"].value) == [{"label": "x"}]
    assert values["tags"].value == MISSING and not values["tags"].extracted
    assert all(v.value == MISSING for v in leaf_values(FIELDS, "not json"))


def test_page_images():
    pdf = pymupdf.open()
    for _ in range(3):
        pdf.new_page()
    images, total = page_images(pdf.tobytes(), max_pages=2)
    assert total == 3 and len(images) == 2
    assert images[0]["image_url"]["url"].startswith("data:image/png;base64,")
    with pytest.raises(ValueError, match="Unsupported"):
        page_images(b"plain text", max_pages=None)
