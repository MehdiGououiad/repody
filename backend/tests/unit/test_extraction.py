import io
import json

import pypdfium2 as pdfium
import pytest

from repody.extraction.fields import leaf_values
from repody.extraction.nuextract import instructions, markdown_request, structured_request, template
from repody.extraction.render import page_images
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
    kwargs = request["extra_body"]["chat_template_kwargs"]
    assert json.loads(kwargs["template"])["total"] == "number"
    assert kwargs["instructions"] == (
        "French invoice.\n\nField guidance:\n- total: Amount due\n- vendor.name: Legal name"
    )
    assert instructions(DocumentDef(id="d")) == ""
    assert markdown_request("m")["extra_body"]["chat_template_kwargs"]["mode"] == "markdown"


def test_leaf_values_keep_json_types():
    answer = json.dumps(
        {
            "total": 6000,
            "currency": "MAD",
            "vendor": {"name": " Acme "},
            "lines": [{"label": "x"}],
            "tags": [],
        }
    )
    values = {v.key: v for v in leaf_values(FIELDS, answer)}
    assert values["total"].value == 6000
    assert values["vendor.name"].value == "Acme"
    assert values["lines"].value == [{"label": "x"}]
    assert values["tags"].value is None
    assert not values["tags"].extracted
    assert all(v.value is None for v in leaf_values(FIELDS, "not json"))


def test_page_images():
    pdf = pdfium.PdfDocument.new()
    for _ in range(3):
        pdf.new_page(595, 842)
    buffer = io.BytesIO()
    pdf.save(buffer)
    images, total = page_images(buffer.getvalue(), "application/pdf", max_pages=2)
    assert total == 3 and len(images) == 2
    assert images[0]["image_url"]["url"].startswith("data:image/png;base64,")
    with pytest.raises(ValueError, match="Unsupported"):
        page_images(b"plain text", "text/plain", max_pages=None)


def test_lightonocr_pages_follow_the_official_client():
    from PIL import Image

    from repody.extraction import lightonocr

    pdf = pdfium.PdfDocument.new()
    pdf.new_page(595, 842)  # A4 in points
    buffer = io.BytesIO()
    pdf.save(buffer)
    [page], total = lightonocr.page_images(buffer.getvalue(), "application/pdf", max_pages=None)
    assert total == 1 and max(page.size) == 2048  # rendered at the model's longest edge

    small = io.BytesIO()
    Image.new("RGB", (800, 600), "white").save(small, "PNG")
    [image], _ = lightonocr.page_images(small.getvalue(), "image/png", max_pages=None)
    assert image.size == (800, 600)  # never upscaled

    large = io.BytesIO()
    Image.new("RGB", (4000, 3000), "white").save(large, "PNG")
    [image], _ = lightonocr.page_images(large.getvalue(), "image/png", max_pages=None)
    assert image.size == (2048, 1536)
