from __future__ import annotations

from audit_workbench.settings import Settings
from audit_workbench.storage.mime import (
    OCTET,
    is_allowed_mime,
    normalize_declared_mime,
    sanitize_filename,
    sniff_mime,
)


class UploadValidationError(ValueError):
    pass


def validate_upload_file(
    *,
    filename: str | None,
    declared_mime: str | None,
    data: bytes,
    settings: Settings,
) -> tuple[str, str]:
    if len(data) == 0:
        raise UploadValidationError("Empty file upload is not allowed.")
    if len(data) > settings.max_upload_bytes:
        raise UploadValidationError(
            f"File exceeds maximum size of {settings.max_upload_bytes} bytes."
        )

    safe_name = sanitize_filename(filename or "document")
    allowed = set(settings.upload_allowed_mime_types)
    declared_norm = normalize_declared_mime(declared_mime)
    sniffed_mime = sniff_mime(data)
    if sniffed_mime is None and declared_norm in allowed:
        raise UploadValidationError(
            f"File content does not match declared type: {declared_norm}."
        )
    if (
        sniffed_mime is not None
        and declared_norm not in {OCTET, sniffed_mime}
        and declared_norm in allowed
    ):
        raise UploadValidationError(
            f"File content type {sniffed_mime} does not match declared type {declared_norm}."
        )

    verified_mime = sniffed_mime or declared_norm
    if not is_allowed_mime(verified_mime, allowed):
        raise UploadValidationError(
            f"Unsupported file type: {verified_mime}. Allowed: {', '.join(sorted(allowed))}."
        )
    return safe_name, verified_mime


def validate_upload_batch(*, file_count: int, settings: Settings) -> None:
    if file_count <= 0:
        return
    if file_count > settings.max_upload_files:
        raise UploadValidationError(
            f"Too many files ({file_count}). Maximum is {settings.max_upload_files}."
        )
