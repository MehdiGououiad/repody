"""Shared helpers for NuExtract PDF page limits."""


def pages_to_process(doc_page_count: int, max_pages: int) -> int:
    """Clamp document page count to the NuExtract per-request limit."""
    if doc_page_count <= 0:
        return 0
    return min(doc_page_count, max(1, max_pages))
