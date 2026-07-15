from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DocumentBundle:
    """In-memory document bytes for NuExtract vision extraction."""

    raw_bytes: bytes
    mime_type: str
    page_count: int = 0


def load_document_bundle(
    document_bytes: bytes,
    mime_type: str,
    *,
    settings: object | None = None,
) -> DocumentBundle:
    """Wrap uploaded bytes; page count is set when pages are rendered for VLM."""
    _ = settings
    mime = (mime_type or "").lower()
    return DocumentBundle(raw_bytes=document_bytes, mime_type=mime_type or mime)
