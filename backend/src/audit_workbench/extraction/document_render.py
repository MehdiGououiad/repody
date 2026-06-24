"""Per-model document input policies (upstream docs only, no platform tuning).

NuExtract3: native image bytes; PDF → lossless PNG @ 170 DPI (official example).
Surya OCR 2: PIL from native bytes; PDF → lossless PNG @ IMAGE_DPI (96 in benchmarks).
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from PIL import Image

    from audit_workbench.extraction.document_bundle import DocumentBundle
    from audit_workbench.settings import Settings

RenderFormat = Literal["native", "png"]


@dataclass(frozen=True)
class ModelRenderPolicy:
    """How the platform prepares bytes before calling a model adapter."""

    model_id: str
    doc_ref: str
    image_input: Literal["native_bytes", "pil_rgb"]
    pdf_dpi: int
    pdf_format: Literal["png"]
    max_edge_px: int | None = None


# https://huggingface.co/numind/NuExtract3 — pdf_to_png_data_urls(..., dpi=170)
REPODY_VLM_RENDER = ModelRenderPolicy(
    model_id="repody:vlm",
    doc_ref="numind/NuExtract3 (dpi=170 PNG, native image uploads)",
    image_input="native_bytes",
    pdf_dpi=170,
    pdf_format="png",
    max_edge_px=None,
)

# https://huggingface.co/datalab-to/surya-ocr-2 — Image.open(path); 96 DPI benchmark input
SURYA_OCR_RENDER = ModelRenderPolicy(
    model_id="surya:ocr2",
    doc_ref="datalab-to/surya-ocr-2 (native image; PDF raster @ IMAGE_DPI)",
    image_input="pil_rgb",
    pdf_dpi=96,
    pdf_format="png",
    max_edge_px=None,
)

RENDER_POLICIES: dict[str, ModelRenderPolicy] = {
    REPODY_VLM_RENDER.model_id: REPODY_VLM_RENDER,
    SURYA_OCR_RENDER.model_id: SURYA_OCR_RENDER,
}


def _is_pdf(mime_type: str, raw_bytes: bytes) -> bool:
    mime = (mime_type or "").lower()
    return mime == "application/pdf" or raw_bytes.startswith(b"%PDF")


def _is_image_upload(mime_type: str, raw_bytes: bytes) -> bool:
    if _is_pdf(mime_type, raw_bytes):
        return False
    mime = (mime_type or "").lower()
    return mime.startswith("image/")


def repody_vlm_pdf_dpi(settings: Settings) -> int:
    return settings.repody_vlm_pdf_dpi


def surya_pdf_dpi(settings: Settings) -> int:
    return settings.surya_image_dpi


def native_image_mime_type(mime_type: str, image_bytes: bytes) -> str:
    mime = (mime_type or "").lower()
    if mime == "image/png" or image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if mime in {"image/webp", "image/x-webp"} or image_bytes.startswith(b"RIFF"):
        return "image/webp"
    if mime in {"image/jpeg", "image/jpg"} or image_bytes.startswith(b"\xff\xd8"):
        return "image/jpeg"
    return "image/jpeg"


def repody_vlm_pages(bundle: DocumentBundle, settings: Settings) -> tuple[list[tuple[bytes, str]], int]:
    """Pages for Repody VLM: native uploads; PDF → lossless PNG per NuExtract docs."""
    if _is_image_upload(bundle.mime_type, bundle.raw_bytes):
        bundle.page_count = 1
        mime = native_image_mime_type(bundle.mime_type, bundle.raw_bytes)
        return [(bundle.raw_bytes, mime)], 1

    if _is_pdf(bundle.mime_type, bundle.raw_bytes):
        from audit_workbench.extraction.preprocess import render_pdf_pages_png

        pages = render_pdf_pages_png(
            bundle.raw_bytes,
            settings=settings,
            dpi=repody_vlm_pdf_dpi(settings),
            max_edge=REPODY_VLM_RENDER.max_edge_px,
        )
        bundle.page_count = len(pages)
        return [(page, "image/png") for page in pages], len(pages)

    from audit_workbench.extraction.preprocess import render_document_pages_jpeg

    pages = render_document_pages_jpeg(bundle.raw_bytes, bundle.mime_type, settings=settings)
    bundle.page_count = len(pages)
    return [(page, "image/jpeg") for page in pages], len(pages)


def surya_pil_pages(bundle: DocumentBundle, settings: Settings) -> list[Image.Image]:
    """PIL pages for Surya: native uploads; PDF → lossless PNG @ surya_image_dpi."""
    from PIL import Image

    if _is_image_upload(bundle.mime_type, bundle.raw_bytes):
        image = Image.open(io.BytesIO(bundle.raw_bytes))
        image.load()
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        bundle.page_count = 1
        return [image]

    if _is_pdf(bundle.mime_type, bundle.raw_bytes):
        from audit_workbench.extraction.preprocess import render_pdf_pages_png

        png_pages = render_pdf_pages_png(
            bundle.raw_bytes,
            settings=settings,
            dpi=surya_pdf_dpi(settings),
            max_edge=SURYA_OCR_RENDER.max_edge_px,
        )
        bundle.page_count = len(png_pages)
        images: list[Image.Image] = []
        for page in png_pages:
            image = Image.open(io.BytesIO(page))
            image.load()
            images.append(image)
        return images

    image = Image.open(io.BytesIO(bundle.raw_bytes))
    image.load()
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    bundle.page_count = 1
    return [image]
