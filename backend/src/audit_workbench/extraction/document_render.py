"""Per-model document input policies (upstream docs only, no platform tuning).

NuExtract3-GGUF: native image bytes; PDF → lossless PNG @ 170 DPI via PyMuPDF (official example).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from audit_workbench.extraction.document_bundle import DocumentBundle


@dataclass(frozen=True)
class ModelRenderPolicy:
    """How the platform prepares bytes before calling a model adapter."""

    model_id: str
    doc_ref: str
    image_input: Literal["native_bytes", "pil_rgb"]
    pdf_dpi: int
    pdf_format: Literal["png"]
    max_edge_px: int | None = None


# https://huggingface.co/numind/NuExtract3-GGUF — pdf_to_png_data_urls(..., dpi=170)
REPODY_VLM_RENDER = ModelRenderPolicy(
    model_id="repody:vlm",
    doc_ref="numind/NuExtract3 (dpi=170 PNG, native image uploads)",
    image_input="native_bytes",
    pdf_dpi=170,
    pdf_format="png",
    max_edge_px=None,
)

RENDER_POLICIES: dict[str, ModelRenderPolicy] = {
    REPODY_VLM_RENDER.model_id: REPODY_VLM_RENDER,
}


def _is_pdf(mime_type: str, raw_bytes: bytes) -> bool:
    mime = (mime_type or "").lower()
    return mime == "application/pdf" or raw_bytes.startswith(b"%PDF")


def _is_image_upload(mime_type: str, raw_bytes: bytes) -> bool:
    if _is_pdf(mime_type, raw_bytes):
        return False
    mime = (mime_type or "").lower()
    return mime.startswith("image/")


def native_image_mime_type(mime_type: str, image_bytes: bytes) -> str:
    mime = (mime_type or "").lower()
    if mime == "image/png" or image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if mime in {"image/webp", "image/x-webp"} or image_bytes.startswith(b"RIFF"):
        return "image/webp"
    if mime in {"image/jpeg", "image/jpg"} or image_bytes.startswith(b"\xff\xd8"):
        return "image/jpeg"
    return "image/jpeg"


def repody_vlm_pages(
    bundle: DocumentBundle,
) -> tuple[list[tuple[bytes, str]], int]:
    """Pages for Repody VLM: native uploads; PDF → PNG @ official DPI."""
    if _is_image_upload(bundle.mime_type, bundle.raw_bytes):
        bundle.page_count = 1
        mime = native_image_mime_type(bundle.mime_type, bundle.raw_bytes)
        return [(bundle.raw_bytes, mime)], 1

    if _is_pdf(bundle.mime_type, bundle.raw_bytes):
        from audit_workbench.extraction.preprocess import render_nuextract_pdf_pages

        pages = render_nuextract_pdf_pages(bundle.raw_bytes)
        bundle.page_count = len(pages)
        return [(page, "image/png") for page in pages], len(pages)

    raise ValueError(
        f"Unsupported document type for NuExtract vision: {bundle.mime_type!r}. "
        "Upload a PDF or image (PNG, JPEG, WebP)."
    )
