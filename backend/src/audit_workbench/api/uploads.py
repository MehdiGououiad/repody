from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.api.deps import get_session
from audit_workbench.auth.dependencies import get_current_principal
from audit_workbench.auth.principal import Principal
from audit_workbench.schemas.uploads import (
    ConfirmUploadItem,
    ConfirmUploadRequest,
    ConfirmUploadResponse,
    PresignRequest,
    PresignResponse,
    PresignedUploadItem,
    UploadCapabilitiesResponse,
    UploadItem,
    UploadResponse,
)
from audit_workbench.services.upload_intents import (
    UploadIntentError,
    confirm_upload_intent,
    record_upload_intent,
)
from audit_workbench.services.upload_validation import (
    UploadValidationError,
    validate_upload_batch,
    validate_upload_file,
)
from audit_workbench.settings import get_settings
from audit_workbench.storage.base import PresignedPut
from audit_workbench.storage.factory import get_storage
from audit_workbench.storage.mime import is_allowed_mime, sanitize_filename

router = APIRouter(prefix="/uploads", tags=["uploads"])


def _presign_supported() -> bool:
    settings = get_settings()
    return settings.storage_backend == "s3" and settings.direct_upload_enabled


@router.get("/capabilities", response_model=UploadCapabilitiesResponse)
async def upload_capabilities() -> UploadCapabilitiesResponse:
    settings = get_settings()
    presigned = _presign_supported()
    return UploadCapabilitiesResponse(
        storage_backend=settings.storage_backend,
        direct_upload_enabled=settings.direct_upload_enabled and presigned,
        upload_mode="presigned" if presigned else "api",
        max_upload_bytes=settings.max_upload_bytes,
        max_upload_files=settings.max_upload_files,
    )


@router.post("/presign", response_model=PresignResponse)
async def presign_uploads(
    body: PresignRequest,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> PresignResponse:
    settings = get_settings()
    validate_upload_batch(file_count=len(body.files), settings=settings)

    if not _presign_supported():
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
                for f in body.files
            ],
        )

    allowed = set(settings.upload_allowed_mime_types)
    storage = get_storage()
    items: list[PresignedUploadItem] = []

    for file_req in body.files:
        if file_req.size > settings.max_upload_bytes:
            raise HTTPException(
                400,
                f"File {file_req.file_name} exceeds maximum size of {settings.max_upload_bytes} bytes.",
            )
        if not is_allowed_mime(file_req.mime_type, allowed):
            raise HTTPException(
                400,
                f"Unsupported file type: {file_req.mime_type}.",
            )

        upload_id = uuid.uuid4().hex
        safe_name = sanitize_filename(file_req.file_name)
        key = f"runs/{upload_id}/{safe_name}"
        presigned: PresignedPut = await storage.presign_put(
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
            owner_subject=principal.subject,
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

    return PresignResponse(upload_mode="presigned", uploads=items)


@router.post("/confirm", response_model=ConfirmUploadResponse)
async def confirm_uploads(
    body: ConfirmUploadRequest,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> ConfirmUploadResponse:
    settings = get_settings()
    storage = get_storage()
    confirmed: list[ConfirmUploadItem] = []

    for key in body.storage_keys:
        try:
            size, _content_type = await storage.stat_object(key)
            sample = await storage.head_bytes(key, max_bytes=4096)
        except FileNotFoundError as exc:
            raise HTTPException(404, f"Upload not found: {key}") from exc
        except Exception as exc:
            raise HTTPException(503, "Storage unavailable") from exc

        if size == 0:
            raise HTTPException(400, f"Upload empty: {key}")
        if size > settings.max_upload_bytes:
            file_name = key.rsplit("/", 1)[-1]
            raise HTTPException(
                400,
                f"File {file_name} exceeds maximum size of {settings.max_upload_bytes} bytes.",
            )

        file_name = key.rsplit("/", 1)[-1]
        try:
            _safe_name, verified_mime = validate_upload_file(
                filename=file_name,
                declared_mime=None,
                data=sample,
                settings=settings,
            )
        except UploadValidationError as exc:
            raise HTTPException(400, str(exc)) from exc

        try:
            intent = await confirm_upload_intent(
                session,
                storage_key=key,
                size=size,
                verified_mime=verified_mime,
                owner_subject=principal.subject,
            )
        except UploadIntentError as exc:
            raise HTTPException(400, str(exc)) from exc

        confirmed.append(
            ConfirmUploadItem(
                storage_key=key,
                file_name=intent.file_name,
                mime_type=intent.mime_type,
                size=size,
            )
        )

    return ConfirmUploadResponse(uploads=confirmed)


@router.post("", response_model=UploadResponse, status_code=201)
async def upload_files(files: list[UploadFile] = File(...)) -> UploadResponse:
    settings = get_settings()
    validate_upload_batch(file_count=len(files), settings=settings)
    storage = get_storage()
    items: list[UploadItem] = []
    for upload in files:
        data = await upload.read()
        try:
            safe_name, verified_mime = validate_upload_file(
                filename=upload.filename,
                declared_mime=upload.content_type,
                data=data,
                settings=settings,
            )
        except UploadValidationError as exc:
            raise HTTPException(400, str(exc)) from exc

        upload_id = uuid.uuid4().hex
        key = f"uploads/{upload_id}/{safe_name}"
        await storage.put_bytes(key, data, verified_mime)
        items.append(
            UploadItem(
                id=upload_id,
                storage_key=key,
                file_name=safe_name,
                mime_type=verified_mime,
                size=len(data),
            )
        )
    return UploadResponse(uploads=items)
