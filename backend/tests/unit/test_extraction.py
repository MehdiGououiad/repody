import base64
import io
import json

import pypdfium2 as pdfium
import pytest
from PIL import Image

from repody.extraction import lightonocr, nuextract
from repody.extraction.fields import leaf_values
from repody.extraction.nuextract import instructions, markdown_request, structured_request, template
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


def _pdf(pages: int) -> bytes:
    pdf = pdfium.PdfDocument.new()
    for _ in range(pages):
        pdf.new_page(595, 842)  # A4 in points
    buffer = io.BytesIO()
    pdf.save(buffer)
    return buffer.getvalue()


def _png(width: int, height: int) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(buffer, "PNG")
    return buffer.getvalue()


def _size(part: dict) -> tuple[int, int]:
    data = base64.b64decode(part["image_url"]["url"].split(",", 1)[1])
    return Image.open(io.BytesIO(data)).size


def test_nuextract_pages_at_170_dpi_and_images_as_uploaded():
    parts, total = nuextract.page_parts(_pdf(3), "application/pdf", max_pages=2)
    assert total == 3 and len(parts) == 2
    width, height = _size(parts[0])
    assert abs(width - 595 * 170 / 72) < 1 and abs(height - 842 * 170 / 72) < 1  # 170 DPI
    jpeg = io.BytesIO()
    Image.new("RGB", (10, 10)).save(jpeg, "JPEG")
    [part], total = nuextract.page_parts(jpeg.getvalue(), "image/jpeg", max_pages=None)
    assert total == 1
    assert (
        part["image_url"]["url"]
        == "data:image/jpeg;base64," + base64.b64encode(jpeg.getvalue()).decode()
    )


def test_lightonocr_pages_follow_the_official_client():
    [page], total = lightonocr.page_parts(_pdf(1), "application/pdf", max_pages=None)
    assert total == 1 and max(_size(page)) == 2048  # rendered at the model's longest edge
    [image], _ = lightonocr.page_parts(_png(800, 600), "image/png", max_pages=None)
    assert _size(image) == (800, 600)  # never upscaled
    [image], _ = lightonocr.page_parts(_png(4000, 3000), "image/png", max_pages=None)
    assert _size(image) == (2048, 1536)
