import base64
import io
import json

import pypdfium2 as pdfium
import pytest
from PIL import ExifTags, Image

from repody.extraction import nuextract, render
from repody.extraction.fields import leaf_values, parse_answer
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
    assert request["temperature"] == 0.2  # the card's in-context example
    assert request["messages"][0]["role"] == "developer"
    assert request["messages"][-1] == {"role": "user", "content": []}
    kwargs = request["extra_body"]["chat_template_kwargs"]
    assert json.loads(kwargs["template"])["total"] == "number"
    assert kwargs["instructions"] == (
        "French invoice.\n\nField guidance:\n- total: Amount due\n- vendor.name: Legal name"
    )
    assert instructions(DocumentDef(id="d")) == ""
    markdown = markdown_request("m")
    assert markdown["extra_body"]["chat_template_kwargs"] == {
        "mode": "markdown",
        "enable_thinking": False,
    }
    assert markdown["temperature"] == 1.0  # the card's document-to-Markdown example


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
    data, error = parse_answer(answer)
    assert error is None
    values = {v.key: v for v in leaf_values(FIELDS, data)}
    assert values["total"].value == 6000
    assert values["vendor.name"].value == "Acme"
    assert values["lines"].value == [{"label": "x"}]
    assert values["tags"].value is None
    assert not values["tags"].extracted


def test_slightly_malformed_answers_are_repaired_and_unusable_ones_reported():
    data, error = parse_answer('{"total": 6000, "currency": "MAD",')  # cut off mid-object
    assert error is None
    assert data == {"total": 6000, "currency": "MAD"}
    assert parse_answer("") == ({}, "The model returned no answer.")
    assert parse_answer('["not", "an", "object"]')[1] == "The model's answer is not a JSON object."
    assert all(v.value is None for v in leaf_values(FIELDS, {}))


def test_unknown_template_types_are_rejected():
    with pytest.raises(ValueError, match="Unknown template type"):
        SchemaField(name="x", template_type="numbr")
    assert SchemaField(name="x", template_type="region:FR").template_type == "region:FR"
    assert SchemaField(name="x", template_type=" ").template_type == "verbatim-string"


def _pdf(pages: int) -> bytes:
    pdf = pdfium.PdfDocument.new()
    for _ in range(pages):
        pdf.new_page(595, 842)  # A4 in points
    buffer = io.BytesIO()
    pdf.save(buffer)
    return buffer.getvalue()


def _image(fmt: str = "PNG", size: tuple[int, int] = (8, 8), *, orientation: int = 1) -> bytes:
    """An encoded image; ``orientation`` is its EXIF orientation tag (6: rotated 90°)."""
    buffer = io.BytesIO()
    exif = Image.Exif()
    exif[ExifTags.Base.Orientation] = orientation
    Image.new("RGB", size, "white").save(buffer, fmt, exif=exif)
    return buffer.getvalue()


def _size(part: dict) -> tuple[int, int]:
    data = base64.b64decode(part["image_url"]["url"].split(",", 1)[1])
    return Image.open(io.BytesIO(data)).size


def test_nuextract_gets_pdf_pages_at_170_dpi_and_images_as_png():
    parts, total = nuextract.page_parts(_pdf(3), "application/pdf", max_pages=2)
    assert total == 3
    assert len(parts) == 2
    width, height = _size(parts[0])
    assert abs(width - 595 * 170 / 72) < 1
    assert abs(height - 842 * 170 / 72) < 1
    for fmt, mime in [("JPEG", "image/jpeg"), ("WEBP", "image/webp"), ("PNG", "image/png")]:
        [part], total = nuextract.page_parts(_image(fmt, (10, 12)), mime, max_pages=None)
        assert total == 1
        assert part["image_url"]["url"].startswith("data:image/png;base64,")  # stb_image reads it
        assert _size(part) == (10, 12)


def test_transparent_images_are_flattened_on_white():
    buffer = io.BytesIO()
    Image.new("RGBA", (4, 4), (0, 0, 0, 0)).save(buffer, "PNG")  # fully transparent black
    flat = render.open_image(buffer.getvalue())
    assert flat.mode == "RGB"
    assert flat.getpixel((0, 0)) == (255, 255, 255)


def test_rotated_photos_are_sent_upright():
    """Phone photos store their rotation in EXIF, which model servers ignore."""
    rotated = _image("JPEG", (40, 20), orientation=6)
    [part], _ = nuextract.page_parts(rotated, "image/jpeg", max_pages=None)
    assert part["image_url"]["url"].startswith("data:image/png;base64,")
    assert _size(part) == (20, 40)


@pytest.mark.parametrize(
    ("data", "mime"),
    [
        (_pdf(1), "application/pdf"),
        (_image("PNG"), "image/png"),
        (_image("JPEG"), "image/jpeg"),
        (_image("WEBP"), "image/webp"),
        (_image("GIF"), None),  # an image, but not one the API accepts
        (b"%PDF-1.7\nnot really a pdf", None),  # a PDF header alone is not a PDF
        (_image("PNG")[:40], None),  # truncated
        (b"plain text", None),
    ],
)
def test_file_type_is_what_the_decoders_can_open(data: bytes, mime: str | None):
    file = io.BytesIO(data)
    file.seek(5)
    assert render.file_type(file) == mime
    assert file.tell() == 0  # rewound for storage


def test_an_oversized_pdf_page_is_drawn_within_the_pixel_cap():
    pdf = pdfium.PdfDocument.new()
    pdf.new_page(200 * 72, 200 * 72)  # 200 x 200 inches: 34 000 px a side at 170 DPI
    buffer = io.BytesIO()
    pdf.save(buffer)
    [part], total = render.pdf_page_parts(buffer.getvalue(), max_pages=None)
    width, height = _size(part)
    assert total == 1
    assert width * height <= render.MAX_RENDER_PIXELS


def test_an_image_bomb_is_refused_from_its_header():
    buffer = io.BytesIO()
    Image.new("1", (10_000, 8_000)).save(buffer, format="PNG")  # 80 MP, a few KB on disk
    assert render.file_type(buffer) is None


def test_an_oversized_image_is_drawn_within_the_pixel_cap():
    buffer = io.BytesIO()
    Image.new("RGB", (6_000, 5_000), "white").save(buffer, format="JPEG")  # 30 MP: allowed
    page = render.open_image(buffer.getvalue())
    assert page.width * page.height <= render.MAX_RENDER_PIXELS
