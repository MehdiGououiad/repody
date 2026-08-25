"""Persisted upload intents for presigned object storage flows."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from repody.infra.db.models import UploadIntent
from repody.infra.storage.mime import mimes_match_for_confirm, normalize_declared_mime
from repody.runtime.contracts.result import AppError, ErrorCode, Result
from repody.runtime.run.contracts import FileBinding


def _validation(message: str) -> AppError:
    return AppError(code=ErrorCode.VALIDATION, message=message)


def _forbidden(message: str) -> AppError:
    return AppError(code=ErrorCode.FORBIDDEN, message=message)


async def record_upload_intent(
    session: AsyncSession,
    *,
    storage_key: str,
    file_name: str,
    mime_type: str,
    size: int,
    document_id: str | None = None,
    owner_subject: str | None = None,
) -> UploadIntent:
    row = UploadIntent(
        id=f"upl-{uuid.uuid4().hex[:12]}",
        storage_key=storage_key,
        file_name=file_name,
        mime_type=normalize_declared_mime(mime_type),
        size=size,
        document_id=document_id,
        owner_subject=owner_subject,
    )
    session.add(row)
    await session.flush()
    return row


async def load_upload_intent(session: AsyncSession, storage_key: str) -> UploadIntent | None:
    result = await session.execute(
        select(UploadIntent).where(UploadIntent.storage_key == storage_key)
    )
    return result.scalar_one_or_none()


def _check_owner(row: UploadIntent, owner_subject: str | None) -> AppError | None:
    """Fail-closed when an intent is owned: caller must present the same subject.

    Workflow API keys resolve to owner_subject=None. They must not bind JWT-owned
    uploads (IDOR). Unowned legacy intents remain usable by machine principals.
    """
    if not row.owner_subject:
        return None
    if owner_subject is None:
        return _forbidden("Upload requires the owning authenticated user.")
    if row.owner_subject != owner_subject:
        return _forbidden("Upload belongs to a different authenticated user.")
    return None


async def confirm_upload_intent(
    session: AsyncSession,
    *,
    storage_key: str,
    size: int,
    verified_mime: str,
    owner_subject: str | None = None,
) -> Result[UploadIntent]:
    row = await load_upload_intent(session, storage_key)
    if row is None:
        return Result.fail(_validation("Upload was not prepared by this API."))
    owner_err = _check_owner(row, owner_subject)
    if owner_err is not None:
        return Result.fail(owner_err)
    if size != row.size:
        return Result.fail(_validation("Upload size does not match the prepared upload."))
    if not mimes_match_for_confirm(prepared=row.mime_type, verified=verified_mime):
        return Result.fail(_validation("Upload MIME type does not match the prepared upload."))
    # Prefer sniffed type when prepare only had a generic browser fallback.
    verified_norm = normalize_declared_mime(verified_mime)
    if normalize_declared_mime(row.mime_type) != verified_norm:
        row.mime_type = verified_norm
    row.confirmed_at = datetime.now(UTC)
    await session.flush()
    return Result.ok(row)


async def bindings_from_confirmed_uploads(
    session: AsyncSession,
    bindings: list[FileBinding],
    *,
    owner_subject: str | None = None,
) -> Result[list[FileBinding]]:
    out: list[FileBinding] = []
    for binding in bindings:
        row = await load_upload_intent(session, binding.storage_key)
        if row is None or row.confirmed_at is None:
            return Result.fail(
                _validation("Run file binding was not confirmed through uploads/confirm.")
            )
        owner_err = _check_owner(row, owner_subject)
        if owner_err is not None:
            return Result.fail(owner_err)
        if binding.document_id and row.document_id and binding.document_id != row.document_id:
            return Result.fail(
                _validation("Run file binding document does not match the upload intent.")
            )
        out.append(
            FileBinding(
                document_id=binding.document_id or row.document_id,
                storage_key=row.storage_key,
                mime_type=row.mime_type,
                file_name=row.file_name,
            )
        )
    return Result.ok(out)
