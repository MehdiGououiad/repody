"""Upload binding helpers for run enqueue (multipart files -> stored FileBindings)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from repody.app.uploads.document_slots import resolve_document_slot_keys
from repody.app.uploads.service import IncomingFile, new_storage_key
from repody.app.uploads.validation import (
    UploadValidationError,
    validate_upload_batch,
    validate_upload_file,
)
from repody.app.workflow.repository import load_workflow
from repody.infra.storage.factory import get_storage
from repody.runtime.contracts.result import AppError, ErrorCode
from repody.runtime.run.contracts import FileBinding
from repody.settings import get_settings


def _invalid(message: str) -> AppError:
    return AppError(ErrorCode.VALIDATION, message)


async def bindings_from_uploads(
    files: Sequence[IncomingFile],
    document_ids: list[str] | None,
) -> list[FileBinding]:
    settings = get_settings()
    try:
        validate_upload_batch(file_count=len(files), settings=settings)
    except UploadValidationError as exc:
        raise _invalid(str(exc)) from exc

    storage = get_storage()
    bindings: list[FileBinding] = []
    for idx, upload in enumerate(files):
        try:
            safe_name, verified_mime = validate_upload_file(
                filename=upload.filename,
                declared_mime=upload.content_type,
                data=upload.data,
                settings=settings,
            )
        except UploadValidationError as exc:
            raise _invalid(str(exc)) from exc

        _upload_id, key = new_storage_key(safe_name)
        await storage.put_bytes(key, upload.data, verified_mime)
        doc_id = document_ids[idx] if document_ids and idx < len(document_ids) else None
        bindings.append(
            FileBinding(
                document_id=doc_id,
                storage_key=key,
                mime_type=verified_mime,
                file_name=safe_name,
            )
        )
    return bindings


def parse_json_form(value: str | None, field_name: str) -> list | dict | None:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise _invalid(f"Invalid JSON in {field_name}.") from exc


def parse_slot_list_form(value: str | None, field_name: str) -> list[str] | None:
    parsed = parse_json_form(value, field_name)
    if parsed is None:
        return None
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise _invalid(f"Invalid JSON in {field_name} — expected an array of strings.")
    return parsed


async def bindings_from_multipart(
    session: AsyncSession,
    workflow_id: str,
    files: Sequence[IncomingFile],
    *,
    document_ids: str | None,
    document_types: str | None,
) -> list[FileBinding]:
    parsed_ids = parse_slot_list_form(document_ids, "document_ids")
    parsed_types = parse_slot_list_form(document_types, "document_types")
    if parsed_ids is not None and parsed_types is not None:
        raise _invalid("Use document_ids or document_types, not both.")
    slot_keys = parsed_types if parsed_types is not None else parsed_ids

    resolved_ids: list[str] | None = None
    if slot_keys is not None:
        wf = await load_workflow(session, workflow_id)
        if not wf:
            raise AppError(ErrorCode.NOT_FOUND, "Workflow not found")
        try:
            resolved_ids = resolve_document_slot_keys(cast(Sequence[Any], wf.documents), slot_keys)
        except ValueError as exc:
            raise _invalid(str(exc)) from exc
        if len(resolved_ids) != len(files):
            raise _invalid(
                "document_ids/document_types length must match the number of uploaded files."
            )

    return await bindings_from_uploads(files, resolved_ids)
