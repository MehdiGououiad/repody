"""Upload binding helpers for Run enqueue — Result at the service boundary."""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from typing import Any, cast

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.platform.contracts.result import AppError, ErrorCode, Result
from audit_workbench.platform.run.contracts import FileBinding
from audit_workbench.services.document_slots import resolve_document_slot_keys
from audit_workbench.services.upload_validation import (
    UploadValidationError,
    validate_upload_batch,
    validate_upload_file,
)
from audit_workbench.services.workflow import load_workflow
from audit_workbench.settings import get_settings
from audit_workbench.storage.factory import get_storage


def _validation_error(message: str) -> AppError:
    return AppError(code=ErrorCode.VALIDATION, message=message)


async def bindings_from_uploads(
    files: list[UploadFile],
    document_ids: list[str] | None,
) -> Result[list[FileBinding]]:
    settings = get_settings()
    try:
        validate_upload_batch(file_count=len(files), settings=settings)
    except UploadValidationError as exc:
        return Result.fail(_validation_error(str(exc)))

    storage = get_storage()
    bindings: list[FileBinding] = []
    for idx, upload in enumerate(files):
        data = await upload.read()
        try:
            safe_name, verified_mime = validate_upload_file(
                filename=upload.filename,
                declared_mime=upload.content_type,
                data=data,
                settings=settings,
            )
        except UploadValidationError as exc:
            return Result.fail(_validation_error(str(exc)))

        upload_id = uuid.uuid4().hex
        key = f"runs/{upload_id}/{safe_name}"
        await storage.put_bytes(key, data, verified_mime)
        doc_id = document_ids[idx] if document_ids and idx < len(document_ids) else None
        bindings.append(
            FileBinding(
                document_id=doc_id,
                storage_key=key,
                mime_type=verified_mime,
                file_name=safe_name,
            )
        )
    return Result.ok(bindings)


def parse_json_form(value: str | None, field_name: str) -> Result[list | dict | None]:
    if not value:
        return Result.ok(None)
    try:
        return Result.ok(json.loads(value))
    except json.JSONDecodeError:
        return Result.fail(_validation_error(f"Invalid JSON in {field_name}."))


def parse_slot_list_form(value: str | None, field_name: str) -> Result[list[str] | None]:
    parsed_r = parse_json_form(value, field_name)
    if not parsed_r.is_ok:
        return Result.fail(parsed_r.error or _validation_error(f"Invalid JSON in {field_name}."))
    parsed = parsed_r.unwrap()
    if parsed is None:
        return Result.ok(None)
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        return Result.fail(
            _validation_error(f"Invalid JSON in {field_name} — expected an array of strings.")
        )
    return Result.ok(parsed)


async def bindings_from_multipart(
    session: AsyncSession,
    workflow_id: str,
    files: list[UploadFile],
    *,
    document_ids: str | None,
    document_types: str | None,
) -> Result[list[FileBinding]]:
    ids_r = parse_slot_list_form(document_ids, "document_ids")
    if not ids_r.is_ok:
        return Result.fail(ids_r.error or _validation_error("Invalid document_ids"))
    types_r = parse_slot_list_form(document_types, "document_types")
    if not types_r.is_ok:
        return Result.fail(types_r.error or _validation_error("Invalid document_types"))

    parsed_ids = ids_r.unwrap()
    parsed_types = types_r.unwrap()
    if parsed_ids is not None and parsed_types is not None:
        return Result.fail(_validation_error("Use document_ids or document_types, not both."))
    slot_keys = parsed_types if parsed_types is not None else parsed_ids

    resolved_ids: list[str] | None = None
    if slot_keys is not None:
        wf = await load_workflow(session, workflow_id)
        if not wf:
            return Result.fail(AppError(code=ErrorCode.NOT_FOUND, message="Workflow not found"))
        try:
            resolved_ids = resolve_document_slot_keys(
                cast(Sequence[Any], wf.documents),
                slot_keys,
            )
        except ValueError as exc:
            return Result.fail(_validation_error(str(exc)))
        if len(resolved_ids) != len(files):
            return Result.fail(
                _validation_error(
                    "document_ids/document_types length must match the number of uploaded files."
                )
            )

    return await bindings_from_uploads(files, resolved_ids)
