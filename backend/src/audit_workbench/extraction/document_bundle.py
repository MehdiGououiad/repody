from __future__ import annotations

from dataclasses import dataclass, field

from audit_workbench.settings import Settings, get_settings


def _render_settings_key(settings: Settings) -> tuple[int, int, int, int, int, bool]:
    return (
        settings.document_render_max_edge_px,
        settings.document_render_pdf_dpi,
        settings.ocr_max_pages,
        settings.ocr_max_pages_hard_cap,
        settings.ocr_jpeg_quality,
        settings.ocr_jpeg_optimize,
    )


@dataclass
class DocumentBundle:
    """Single load of a document: bytes and lazily rendered page images."""

    raw_bytes: bytes
    mime_type: str
    page_count: int = 0
    _image_jpeg: bytes | None = field(default=None, repr=False)
    _image_rendered: bool = field(default=False, repr=False)
    _page_jpeg_cache: dict[tuple[int, int, int, int, int, bool], list[bytes]] = field(
        default_factory=dict,
        repr=False,
    )

    def image_jpeg(self, settings: Settings | None = None) -> bytes:
        """Render first page(s) to JPEG once (shared by document models)."""
        pages = self.page_jpegs(settings)
        return pages[0]

    def page_jpegs(self, settings: Settings | None = None) -> list[bytes]:
        """One JPEG per page; cached per render profile (dpi, edge, quality)."""
        cfg = settings or get_settings()
        cache_key = _render_settings_key(cfg)
        cached = self._page_jpeg_cache.get(cache_key)
        if cached is not None:
            return cached

        from audit_workbench.extraction.preprocess import render_document_pages_jpeg

        pages = render_document_pages_jpeg(
            self.raw_bytes,
            self.mime_type,
            settings=cfg,
        )
        self._page_jpeg_cache[cache_key] = pages
        if pages:
            self.page_count = len(pages)
            if not self._image_rendered:
                self._image_jpeg = pages[0]
                self._image_rendered = True
        return pages


def load_document_bundle(
    document_bytes: bytes,
    mime_type: str,
    *,
    settings: Settings | None = None,
) -> DocumentBundle:
    """Wrap document bytes; page count is set on first render (avoids extra PDF open)."""
    _ = settings
    mime = (mime_type or "").lower()
    return DocumentBundle(raw_bytes=document_bytes, mime_type=mime_type or mime)
