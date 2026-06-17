"""Persisted upload intents for presigned object storage flows."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.models import UploadIntent
from audit_workbench.services.run_service import FileBinding
from audit_workbench.storage.mime import normalize_declared_mime


class UploadIntentError(ValueError):
    pass


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


def _check_owner(row: UploadIntent, owner_subject: str | None) -> None:
    if row.owner_subject and owner_subject and row.owner_subject != owner_subject:
        raise UploadIntentError("Upload belongs to a different authenticated user.")


async def confirm_upload_intent(
    session: AsyncSession,
    *,
    storage_key: str,
    size: int,
    verified_mime: str,
    owner_subject: str | None = None,
) -> UploadIntent:
    row = await load_upload_intent(session, storage_key)
    if row is None:
        raise UploadIntentError("Upload was not prepared by this API.")
    _check_owner(row, owner_subject)
    if size != row.size:
        raise UploadIntentError("Upload size does not match the prepared upload.")
    if normalize_declared_mime(verified_mime) != normalize_declared_mime(row.mime_type):
        raise UploadIntentError("Upload MIME type does not match the prepared upload.")
    row.confirmed_at = datetime.now(UTC)
    await session.flush()
    return row


async def bindings_from_confirmed_uploads(
    session: AsyncSession,
    bindings: list[FileBinding],
    *,
    owner_subject: str | None = None,
) -> list[FileBinding]:
    out: list[FileBinding] = []
    for binding in bindings:
        row = await load_upload_intent(session, binding.storage_key)
        if row is None or row.confirmed_at is None:
            raise UploadIntentError("Run file binding was not confirmed through uploads/confirm.")
        _check_owner(row, owner_subject)
        if binding.document_id and row.document_id and binding.document_id != row.document_id:
            raise UploadIntentError("Run file binding document does not match the upload intent.")
        out.append(
            FileBinding(
                document_id=binding.document_id or row.document_id,
                storage_key=row.storage_key,
                mime_type=row.mime_type,
                file_name=row.file_name,
            )
        )
    return out
