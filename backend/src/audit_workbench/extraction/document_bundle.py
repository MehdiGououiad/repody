from __future__ import annotations

from dataclasses import dataclass, field

from audit_workbench.extraction.pdf_pages import pages_to_process
from audit_workbench.settings import Settings, get_settings


@dataclass
class DocumentBundle:
    """Single load of a document: bytes and lazily rendered page images."""

    raw_bytes: bytes
    mime_type: str
    page_count: int = 0
    _image_jpeg: bytes | None = field(default=None, repr=False)
    _image_rendered: bool = field(default=False, repr=False)
    _page_jpegs: list[bytes] | None = field(default=None, repr=False)
    _pages_rendered: bool = field(default=False, repr=False)

    def image_jpeg(self, settings: Settings | None = None) -> bytes:
        """Render first page(s) to JPEG once (shared by document models)."""
        if self._image_rendered:
            assert self._image_jpeg is not None
            return self._image_jpeg
        from audit_workbench.extraction.preprocess import render_document_to_jpeg

        cfg = settings or get_settings()
        self._image_jpeg = render_document_to_jpeg(
            self.raw_bytes,
            self.mime_type,
            settings=cfg,
        )
        self._image_rendered = True
        return self._image_jpeg

    def page_jpegs(self, settings: Settings | None = None) -> list[bytes]:
        """One JPEG per page for per-page rendering."""
        if self._pages_rendered:
            assert self._page_jpegs is not None
            return self._page_jpegs
        from audit_workbench.extraction.preprocess import render_document_pages_jpeg

        cfg = settings or get_settings()
        self._page_jpegs = render_document_pages_jpeg(
            self.raw_bytes,
            self.mime_type,
            settings=cfg,
        )
        self._pages_rendered = True
        if not self._image_rendered:
            self._image_jpeg = self._page_jpegs[0]
            self._image_rendered = True
        return self._page_jpegs


def load_document_bundle(
    document_bytes: bytes,
    mime_type: str,
    *,
    settings: Settings | None = None,
) -> DocumentBundle:
    """Open PDF/image once and record page count for rendering."""
    cfg = settings or get_settings()
    mime = (mime_type or "").lower()
    bundle = DocumentBundle(raw_bytes=document_bytes, mime_type=mime_type)

    if mime == "application/pdf" or document_bytes[:4] == b"%PDF":
        bundle.page_count = _pdf_page_count(
            document_bytes,
            cfg.ocr_max_pages,
            hard_cap=cfg.ocr_max_pages_hard_cap,
        )
        return bundle

    bundle.page_count = 1
    return bundle


def _pdf_page_count(document_bytes: bytes, max_pages: int, *, hard_cap: int = 50) -> int:
    try:
        import fitz

        doc = fitz.open(stream=document_bytes, filetype="pdf")
        page_count = pages_to_process(len(doc), max_pages, hard_cap=hard_cap)
        doc.close()
        return page_count
    except Exception:
        return 1


def bundle_from_image_bytes(image_bytes: bytes, mime_type: str) -> DocumentBundle:
    """Wrap a pre-rendered image."""
    return DocumentBundle(
        raw_bytes=image_bytes,
        mime_type=mime_type,
        page_count=1,
        _image_jpeg=image_bytes,
        _image_rendered=True,
    )
