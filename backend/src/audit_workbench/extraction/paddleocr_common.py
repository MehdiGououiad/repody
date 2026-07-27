"""Shared helpers for the PP-OCRv6 HTTP pipeline adapter."""

from __future__ import annotations

from typing import Any


# Official fileType: 0 = PDF, 1 = image (incl. TIFF).
FILE_TYPE_PDF = 0
FILE_TYPE_IMAGE = 1


def file_type_for_mime(mime_type: str | None) -> int:
    mime = (mime_type or "").split(";", 1)[0].strip().lower()
    if mime == "application/pdf":
        return FILE_TYPE_PDF
    return FILE_TYPE_IMAGE


def paddle_error_message(body: dict[str, Any], *, label: str) -> str | None:
    """Return an error string when official serving errorCode is non-zero."""
    code = body.get("errorCode")
    if code is None:
        return None
    try:
        if int(code) == 0:
            return None
    except (TypeError, ValueError):
        return f"{label} invalid errorCode: {code!r}"
    return f"{label} error {code}: {body.get('errorMsg') or body}"
