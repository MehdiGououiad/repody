import asyncio
import base64
import io
import json
import math

import httpx2
import openai
import pypdfium2 as pdfium
import pytest
from PIL import ExifTags, Image

from repody.extraction import nuextract, pipeline, render
from repody.extraction.fields import disagreements, leaf_values, parse_answer
from repody.extraction.nuextract import instructions, markdown_request, structured_request, template
from repody.schemas.workflow import DocumentDef, IclExample, SchemaField
from tests.files import LOCKED_PDF, PDF

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
    request = structured_request(doc, "nuextract", max_tokens=4096)
    assert request["temperature"] == 0.2  # the card's non-thinking mode
    assert request["messages"][0]["role"] == "developer"
    assert request["messages"][-1] == {"role": "user", "content": []}
    kwargs = request["extra_body"]["chat_template_kwargs"]
    assert json.loads(kwargs["template"])["total"] == "number"
    assert kwargs["instructions"] == (
        "French invoice.\n\nField guidance:\n- total: Amount due\n- vendor.name: Legal name"
    )
    assert instructions(DocumentDef(id="d")) == ""
    markdown = markdown_request("m", max_tokens=4096)
    assert markdown["extra_body"]["chat_template_kwargs"] == {
        "mode": "markdown",
        "enable_thinking": False,
    }
    assert markdown["temperature"] == 0.2  # the same: 1 measured worse on handwriting
    assert markdown["max_tokens"] == 4096
    # No lists: the answer's size follows the schema (an answer that loops stops early).
    assert request["max_tokens"] == 4096  # tables and lists: as long as they need
    flat = DocumentDef(id="f", schema=[FIELDS[0], FIELDS[3]])  # total, vendor.name
    assert nuextract.answer_budget(flat, 4096) == nuextract.TOKENS_PER_FIELD * (1 + 2)


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


def test_a_single_choice_given_as_a_one_item_list_is_that_choice():
    payment = SchemaField(name="payment", template_type="enum", enum_values=["Virement", "Carte"])
    rows = SchemaField(name="rows", template_type="object-array", children=[payment])
    fields = [payment, rows, FIELDS[1]]
    data = {
        "payment": ["Virement"],
        "rows": [{"payment": ["Carte"]}, {"payment": "Virement"}, "not a row"],
        "currency": ["MAD", "EUR"],  # two choices: left as the model gave them
    }
    values = {v.key: v.value for v in leaf_values(fields, data)}
    assert values["payment"] == "Virement"
    assert values["rows"] == [{"payment": "Carte"}, {"payment": "Virement"}, "not a row"]
    assert values["currency"] == ["MAD", "EUR"]


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


def _pixels(part: dict) -> int:
    width, height = _size(part)
    return width * height


def test_nuextract_gets_pdf_pages_at_170_dpi_and_images_as_png():
    """170 DPI (the model card's), or larger for a page that would be under MIN_MODEL_PIXELS."""
    a3 = pdfium.PdfDocument.new()
    a3.new_page(842, 1191)  # A3: 5.6 MP at 170 DPI, drawn at 170 DPI
    buffer = io.BytesIO()
    a3.save(buffer)
    [part], _ = nuextract.page_parts(buffer.getvalue(), "application/pdf", max_pages=None)
    width, height = _size(part)
    assert abs(width - 842 * 170 / 72) < 1
    assert abs(height - 1191 * 170 / 72) < 1
    for fmt, mime in [("JPEG", "image/jpeg"), ("WEBP", "image/webp"), ("PNG", "image/png")]:
        [part], total = nuextract.page_parts(_image(fmt, (2000, 1600)), mime, max_pages=None)
        assert total == 1
        assert part["image_url"]["url"].startswith("data:image/png;base64,")  # stb_image reads it
        assert _size(part) == (2000, 1600)  # 3.2 MP: as it is


def test_every_page_reaches_the_model_with_at_least_the_minimum_pixels():
    """A small page (an A4 at 170 DPI is 2.8 MP, a photo of an ID card 0.2 MP) is drawn or
    enlarged to MIN_MODEL_PIXELS, its proportions kept."""
    parts, total = nuextract.page_parts(_pdf(3), "application/pdf", max_pages=2)
    assert (total, len(parts)) == (3, 2)
    width, height = _size(parts[0])
    assert width * height == pytest.approx(render.MIN_MODEL_PIXELS, rel=0.002)
    assert width / height == pytest.approx(595 / 842, rel=0.002)
    [part], _ = nuextract.page_parts(_image("JPEG", (515, 321)), "image/jpeg", max_pages=None)
    width, height = _size(part)
    assert width * height == pytest.approx(render.MIN_MODEL_PIXELS, rel=0.002)
    assert width / height == pytest.approx(515 / 321, rel=0.005)


def test_a_second_read_sees_the_page_at_half_the_pixels():
    for data, mime in [(_pdf(1), "application/pdf"), (_image("PNG", (515, 321)), "image/png")]:
        [first], _ = nuextract.page_parts(data, mime, max_pages=None)
        [second], _ = nuextract.page_parts(
            data, mime, max_pages=None, area=pipeline.SECOND_READ_AREA
        )
        assert _pixels(second) == pytest.approx(_pixels(first) / 2, rel=0.005)


def test_report_previews_are_not_enlarged():
    preview = render.page_preview(_pdf(1), render.PDF, 0)
    assert preview is not None
    width, _ = Image.open(io.BytesIO(preview)).size
    assert abs(width - 595 * render.SCREEN_DPI / 72) < 1


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
    width, height = _size(part)
    assert width / height == pytest.approx(0.5, rel=0.01)  # portrait, enlarged


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
    info = render.inspect(file)
    assert (info.mime if info else None) == mime
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
    assert render.inspect(buffer) is None


def test_an_oversized_image_is_drawn_within_the_pixel_cap():
    buffer = io.BytesIO()
    Image.new("RGB", (6_000, 5_000), "white").save(buffer, format="JPEG")  # 30 MP: allowed
    page = render.open_image(buffer.getvalue())
    assert page.width * page.height <= render.MAX_RENDER_PIXELS


def test_pages_reach_the_model_unless_it_refused_or_was_never_reached():
    request = httpx2.Request("POST", "http://model.test/v1/chat/completions")

    def status(code: int) -> openai.APIStatusError:
        return openai.APIStatusError("", response=httpx2.Response(code, request=request), body=None)

    assert pipeline._pages_reached(status(400), 3) == 0
    assert pipeline._pages_reached(status(503), 3) == 3
    assert pipeline._pages_reached(openai.APIConnectionError(request=request), 3) == 0
    assert pipeline._pages_reached(openai.APITimeoutError(request=request), 3) == 3
    assert pipeline._pages_reached(TimeoutError(), 3) == 3


async def test_rendered_pages_in_memory_are_bounded():
    budget = pipeline._PageBudget(40)
    order: list[str] = []

    async def document(name: str, pages: int) -> None:
        async with budget.hold(pages):
            order.append(f"{name} in")
            assert budget.free >= 0
            await asyncio.sleep(0.01)
            order.append(f"{name} out")

    await asyncio.gather(document("a", 30), document("b", 30), document("c", 99))
    # b waits for a; c (more than the budget) takes all of it, alone.
    assert order == ["a in", "a out", "b in", "b out", "c in", "c out"]
    assert budget.free == 40


async def test_a_long_document_is_not_overtaken_by_short_ones():
    budget = pipeline._PageBudget(40)
    order: list[str] = []

    async def document(name: str, pages: int, start: float) -> None:
        await asyncio.sleep(start)
        async with budget.hold(pages):
            order.append(name)
            await asyncio.sleep(0.02)

    await asyncio.gather(
        document("short-1", 20, 0),
        document("short-2", 20, 0),
        document("long", 30, 0.005),  # waits for both shorts
        document("short-3", 5, 0.01),  # would fit beside long's wait, but came after it
    )
    assert order == ["short-1", "short-2", "long", "short-3"]
    assert budget.free == 40


async def test_a_cancelled_wait_gives_nothing_away():
    budget = pipeline._PageBudget(10)
    async with budget.hold(10):
        waiter = asyncio.ensure_future(budget.hold(5).__aenter__())
        await asyncio.sleep(0)
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
    assert budget.free == 10


def test_a_password_protected_pdf_is_told_apart_from_an_unreadable_file():
    with pytest.raises(render.LockedPdfError):
        render.inspect(io.BytesIO(LOCKED_PDF))
    assert render.inspect(io.BytesIO(b"%PDF-1.7 not really")) is None


def test_inspect_gives_each_page_the_pixels_it_is_drawn_with():
    for data, mime in [(PDF, "application/pdf"), (_image("JPEG", (515, 321)), "image/jpeg")]:
        info = render.inspect(io.BytesIO(data))
        assert info is not None
        assert info.page_pixels
        parts, _ = nuextract.page_parts(data, mime, max_pages=1)
        assert info.page_pixels[0] == pytest.approx(_pixels(parts[0]), rel=0.005)


def test_a_requests_tokens_are_its_pages_text_and_answer():
    a4 = 1405 * 1987  # an A4 page at 170 DPI
    doc = DocumentDef.model_validate(
        {
            "id": "d",
            "documentType": "Invoice",
            "schemaFields": [{"name": "total", "type": "number"}],
        }
    )
    one, thirty = pipeline.request_tokens(doc, [a4]), pipeline.request_tokens(doc, [a4] * 30)
    assert thirty - one == 29 * math.ceil(a4 / (32 * 32))  # ~2.7k tokens a page
    assert thirty > 80_000  # 30 A4 pages: ~82k tokens and the answer budget
    small_image = pipeline.request_tokens(doc, [515 * 321])  # raised to ~1 MP by the processor
    assert small_image - pipeline.request_tokens(doc, []) == math.ceil(1024 * 1024 / 1024)


def test_two_reads_disagree_on_values_not_on_case_spacing_or_number_spelling():
    fields = [
        SchemaField(name="name"),
        SchemaField(name="total", template_type="number"),
        SchemaField(name="date", template_type="date"),
        SchemaField(name="lines", template_type="object-array", children=[SchemaField(name="a")]),
    ]
    first = leaf_values(
        fields, {"name": "ACME  SARL", "total": 1317.24, "date": None, "lines": [{"a": "x"}]}
    )
    same = leaf_values(
        fields, {"name": "acme sarl", "total": 1317.240, "date": None, "lines": [{"a": " X "}]}
    )
    assert disagreements(first, same) == {}
    other = leaf_values(fields, {"name": "ACME SARL", "total": 3117.24, "date": "2018-01-21"})
    assert disagreements(first, other) == {"total": 3117.24, "date": "2018-01-21", "lines": None}


def _doc() -> DocumentDef:
    return DocumentDef.model_validate({"id": "d", "documentType": "Bill", "schema": FIELDS[:1]})


@pytest.mark.parametrize(
    ("first", "check", "check_failed", "expected"),
    [
        ('{"total": 1317.24}', '{"total": 1317.24}', False, ("agreed", {})),
        ('{"total": 1317.24}', '{"total": 3117.24}', False, ("disagreed", {"total": 3117.24})),
        ('{"total": 1317.24}', None, True, ("failed", {})),
        ('{"total": 1317.24}', "not json", False, ("failed", {})),
        ('{"total": 1317.24}', None, False, (None, {})),  # no second read
    ],
)
def test_the_second_read_confirms_or_flags_the_first(first, check, check_failed, expected):
    answer = pipeline._Answer(answer=first, check=check, check_failed=check_failed)
    fields = leaf_values(_doc().schema_fields, parse_answer(first)[0])
    assert pipeline._compare(_doc(), fields, answer) == expected


@pytest.mark.parametrize(
    ("mode", "mime", "fields", "twice"),
    [
        ("all", "application/pdf", True, True),
        ("images", "application/pdf", True, False),
        ("images", "image/jpeg", True, True),
        ("off", "image/jpeg", True, False),
        ("all", "image/jpeg", False, False),  # Markdown: nothing to compare
    ],
)
def test_which_documents_are_read_twice(monkeypatch, mode, mime, fields, twice):
    monkeypatch.setattr(pipeline, "get_settings", lambda: type("S", (), {"second_read": mode}))
    doc = DocumentDef.model_validate({"id": "d", "schema": FIELDS[:1] if fields else []})
    assert pipeline._reads_twice(doc, mime) is twice
