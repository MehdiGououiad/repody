from __future__ import annotations

import re

import filetype

PDF = "application/pdf"
JPEG = "image/jpeg"
PNG = "image/png"
WEBP = "image/webp"
OCTET = "application/octet-stream"

_FILETYPE_TO_MIME = {
    "pdf": PDF,
    "png": PNG,
    "jpg": JPEG,
    "jpeg": JPEG,
    "webp": WEBP,
}


def sniff_mime(data: bytes) -> str | None:
    """Magic-byte detection via the filetype library."""
    if not data:
        return None
    kind = filetype.guess(data)
    if kind is None:
        return None
    return _FILETYPE_TO_MIME.get(kind.extension)


def normalize_declared_mime(mime: str | None) -> str:
    raw = (mime or OCTET).split(";", 1)[0].strip().lower()
    if raw == "image/jpg":
        return JPEG
    return raw or OCTET


def resolve_mime(*, data: bytes, declared: str | None) -> str:
    """Prefer magic-byte sniff; fall back to declared MIME when compatible."""
    sniffed = sniff_mime(data)
    declared_norm = normalize_declared_mime(declared)
    if sniffed:
        return sniffed
    return declared_norm


def is_allowed_mime(mime: str, allowed: set[str]) -> bool:
    return normalize_declared_mime(mime) in allowed


def mimes_match_for_confirm(*, prepared: str | None, verified: str | None) -> bool:
    """True when sniffed content MIME is compatible with the prepare-time declaration.

    Browsers often send ``File.type`` / extension-based MIME that disagrees with
    magic bytes (e.g. ``*.png`` that is actually JPEG). Confirm always sniffs
    content; accept when:

    - types match after normalize, or
    - prepare was generic ``application/octet-stream``, or
    - both are concrete types (sniff wins; row is updated to verified).
    """
    prep = normalize_declared_mime(prepared)
    ver = normalize_declared_mime(verified)
    if prep == ver:
        return True
    if prep == OCTET:
        return ver != OCTET
    # Prepared was a concrete type; verified sniffed something else concrete.
    # Trust content — validate_upload_file already enforced the allow-list.
    return ver != OCTET


_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(name: str) -> str:
    base = (name or "document").replace("\\", "/").split("/")[-1].strip()
    base = _SAFE_FILENAME.sub("_", base).strip("._")
    return base[:200] or "document"
