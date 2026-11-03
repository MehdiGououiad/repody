"""Upload use cases: capabilities, presigned PUT, confirmation, and direct storage."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from repody.app.uploads.intents import confirm_upload_intent, record_upload_intent
from repody.app.uploads.validation import (
    UploadValidationError,
    validate_upload_batch,
    validate_upload_file,
)
from repody.infra.storage.factory import get_storage
from repody.infra.storage.mime import is_allowed_mime, sanitize_filename
from repody.runtime.contracts.result import AppError, ErrorCode
from repody.schemas.uploads import (
    ConfirmUploadItem,
    ConfirmUploadResponse,
    PresignedUploadItem,
    PresignFileRequest,
    PresignResponse,
    UploadCapabilitiesResponse,
    UploadItem,
    UploadResponse,
)
from repody.settings import Settings, get_settings

_MIME_SNIFF_BYTES = 4096


@dataclass(frozen=True, slots=True)
class IncomingFile:
    """File bytes received over HTTP, decoupled from the web framework."""

    filename: str | None
    content_type: str | None
    data: bytes


def _bad_request(message: str) -> AppError:
    return AppError(code=ErrorCode.BAD_REQUEST, message=message)


def _too_large(file_name: str, settings: Settings) -> AppError:
    return _bad_request(
        f"File {file_name} exceeds maximum size of {settings.max_upload_bytes} bytes."
    )


def new_storage_key(safe_name: str) -> tuple[str, str]:
    """Return ``(upload_id, storage_key)`` for a new object."""
    upload_id = uuid.uuid4().hex
    return upload_id, f"uploads/{upload_id}/{safe_name}"


def presign_supported(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return settings.direct_upload_enabled


def check_batch_size(file_count: int) -> None:
    try:
        validate_upload_batch(file_count=file_count, settings=get_settings())
    except UploadValidationError as exc:
        raise _bad_request(str(exc)) from exc
    return


def upload_capabilities() -> UploadCapabilitiesResponse:
    settings = get_settings()
    presigned = presign_supported(settings)
    return UploadCapabilitiesResponse(
        direct_upload_enabled=presigned,
        upload_mode="presigned" if presigned else "api",
        max_upload_bytes=settings.max_upload_bytes,
        max_upload_files=settings.max_upload_files,
    )


async def presign_uploads(
    session: AsyncSession,
    files: Sequence[PresignFileRequest],
    *,
    owner_subject: str,
) -> PresignResponse:
    """Record upload intents and return presigned PUT URLs (or ``api`` mode fallback)."""
    check_batch_size(len(files))

    settings = get_settings()
    if not presign_supported(settings):
        return PresignResponse(
            upload_mode="api",
            uploads=[
                PresignedUploadItem(
                    id=uuid.uuid4().hex,
                    storage_key="",
                    file_name=f.file_name,
                    mime_type=f.mime_type,
                    size=f.size,
                    document_id=f.document_id,
                )
                for f in files
            ],
        )

    allowed = set(settings.upload_allowed_mime_types)
    storage = get_storage()
    items: list[PresignedUploadItem] = []
    for file_req in files:
        if file_req.size > settings.max_upload_bytes:
            raise _too_large(file_req.file_name, settings)
        if not is_allowed_mime(file_req.mime_type, allowed):
            raise _bad_request(f"Unsupported file type: {file_req.mime_type}.")

        safe_name = sanitize_filename(file_req.file_name)
        upload_id, key = new_storage_key(safe_name)
        presigned = await storage.presign_put(
            key,
            file_req.mime_type,
            expires_seconds=settings.presigned_upload_ttl_seconds,
        )
        await record_upload_intent(
            session,
            storage_key=key,
            file_name=safe_name,
            mime_type=file_req.mime_type,
            size=file_req.size,
            document_id=file_req.document_id,
            owner_subject=owner_subject,
        )
        items.append(
            PresignedUploadItem(
                id=upload_id,
                storage_key=key,
                file_name=safe_name,
                mime_type=file_req.mime_type,
                size=file_req.size,
                document_id=file_req.document_id,
                upload_url=presigned.upload_url,
                method=presigned.method,
                headers=presigned.headers,
            )
        )

    await session.commit()
    return PresignResponse(upload_mode="presigned", uploads=items)


async def confirm_uploads(
    session: AsyncSession,
    storage_keys: Sequence[str],
    *,
    owner_subject: str,
) -> ConfirmUploadResponse:
    """Verify presigned objects exist, match their intent, and have an allowed MIME type."""
    settings = get_settings()
    storage = get_storage()
    confirmed: list[ConfirmUploadItem] = []

    for key in storage_keys:
        file_name = key.rsplit("/", 1)[-1]
        try:
            size, _content_type = await storage.stat_object(key)
            sample = await storage.head_bytes(key, max_bytes=_MIME_SNIFF_BYTES)
        except FileNotFoundError:
            raise (AppError(code=ErrorCode.NOT_FOUND, message=f"Upload not found: {key}")) from None
        except Exception:
            raise AppError(code=ErrorCode.INFRA, message="Storage unavailable") from None

        if size == 0:
            raise _bad_request(f"Upload empty: {key}")
        if size > settings.max_upload_bytes:
            raise _too_large(file_name, settings)
        try:
            _safe_name, verified_mime = validate_upload_file(
                filename=file_name,
                declared_mime=None,
                data=sample,
                settings=settings,
            )
        except UploadValidationError as exc:
            raise _bad_request(str(exc)) from exc

        intent = await confirm_upload_intent(
            session,
            storage_key=key,
            size=size,
            verified_mime=verified_mime,
            owner_subject=owner_subject,
        )
        confirmed.append(
            ConfirmUploadItem(
                storage_key=key,
                file_name=intent.file_name,
                mime_type=intent.mime_type,
                size=size,
            )
        )

    await session.commit()
    return ConfirmUploadResponse(uploads=confirmed)


async def store_uploads(files: Sequence[IncomingFile]) -> UploadResponse:
    """Validate and store files sent through the API (non-presigned mode)."""
    check_batch_size(len(files))

    settings = get_settings()
    storage = get_storage()
    items: list[UploadItem] = []
    for upload in files:
        try:
            safe_name, verified_mime = validate_upload_file(
                filename=upload.filename,
                declared_mime=upload.content_type,
                data=upload.data,
                settings=settings,
            )
        except UploadValidationError as exc:
            raise _bad_request(str(exc)) from exc

        upload_id, key = new_storage_key(safe_name)
        await storage.put_bytes(key, upload.data, verified_mime)
        items.append(
            UploadItem(
                id=upload_id,
                storage_key=key,
                file_name=safe_name,
                mime_type=verified_mime,
                size=len(upload.data),
            )
        )
    return UploadResponse(uploads=items)
