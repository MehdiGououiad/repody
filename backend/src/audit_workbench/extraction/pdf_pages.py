"""Shared helpers for multi-page PDF text and rendering limits."""

from __future__ import annotations

OCR_MAX_PAGES_HARD_CAP = 50


def effective_pdf_page_limit(max_pages: int, *, hard_cap: int = OCR_MAX_PAGES_HARD_CAP) -> int:
    """Pages to process: positive max_pages, or hard_cap when max_pages <= 0 (all pages)."""
    if max_pages <= 0:
        return hard_cap
    return max(1, min(max_pages, hard_cap))


def pages_to_process(
    doc_page_count: int, max_pages: int, *, hard_cap: int = OCR_MAX_PAGES_HARD_CAP
) -> int:
    """Clamp document page count to configured extraction limit."""
    if doc_page_count <= 0:
        return 0
    return min(doc_page_count, effective_pdf_page_limit(max_pages, hard_cap=hard_cap))


def join_page_texts(chunks: list[str]) -> str:
    """Join per-page OCR/text chunks with page markers for the extraction LLM."""
    cleaned = [c.strip() for c in chunks if c and c.strip()]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    parts: list[str] = []
    for idx, text in enumerate(cleaned):
        parts.append(f"--- Page {idx + 1} ---\n{text}")
    return "\n\n".join(parts)
