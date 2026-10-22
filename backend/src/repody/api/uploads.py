from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from repody.api.auth import PrincipalDep
from repody.api.deps import SessionDep
from repody.api.errors import unwrap_or_raise
from repody.app.uploads import service
from repody.app.uploads.service import IncomingFile
from repody.schemas.uploads import (
    ConfirmUploadRequest,
    ConfirmUploadResponse,
    PresignRequest,
    PresignResponse,
    UploadCapabilitiesResponse,
    UploadResponse,
)
from repody.settings import get_settings

router = APIRouter(prefix="/uploads", tags=["uploads"])

_READ_CHUNK_BYTES = 1024 * 1024


async def read_upload_capped(upload: UploadFile, *, max_bytes: int) -> IncomingFile:
    """Read a multipart file with a hard cap so oversized uploads fail before full buffering."""
    too_large = HTTPException(400, f"File exceeds maximum size of {max_bytes} bytes.")
    if isinstance(upload.size, int) and upload.size > max_bytes:
        raise too_large
    chunks: list[bytes] = []
    total = 0
    while chunk := await upload.read(_READ_CHUNK_BYTES):
        total += len(chunk)
        if total > max_bytes:
            raise too_large
        chunks.append(chunk)
    return IncomingFile(
        filename=upload.filename,
        content_type=upload.content_type,
        data=b"".join(chunks),
    )


async def read_uploads(files: list[UploadFile]) -> list[IncomingFile]:
    unwrap_or_raise(service.check_batch_size(len(files)))
    max_bytes = get_settings().max_upload_bytes
    return [await read_upload_capped(upload, max_bytes=max_bytes) for upload in files]


@router.get("/capabilities", response_model=UploadCapabilitiesResponse)
async def upload_capabilities() -> UploadCapabilitiesResponse:
    return service.upload_capabilities()


@router.post("/presign", response_model=PresignResponse)
async def presign_uploads(
    body: PresignRequest,
    session: SessionDep,
    principal: PrincipalDep,
) -> PresignResponse:
    result = await service.presign_uploads(session, body.files, owner_subject=principal.subject)
    return unwrap_or_raise(result)


@router.post("/confirm", response_model=ConfirmUploadResponse)
async def confirm_uploads(
    body: ConfirmUploadRequest,
    session: SessionDep,
    principal: PrincipalDep,
) -> ConfirmUploadResponse:
    result = await service.confirm_uploads(
        session, body.storage_keys, owner_subject=principal.subject
    )
    return unwrap_or_raise(result)


@router.post("", response_model=UploadResponse, status_code=201)
async def upload_files(files: list[UploadFile] = File(...)) -> UploadResponse:
    return unwrap_or_raise(await service.store_uploads(await read_uploads(files)))
