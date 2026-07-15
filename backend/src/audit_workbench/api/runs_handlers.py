"""Run route helpers — multipart/JSON binding and snapshot parsing."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.auth.run_access import resolve_owner_subject
from audit_workbench.schemas.run_requests import RunSnapshotBody, StoredFileBinding
from audit_workbench.schemas.workflow import DocumentDefSchema, WorkflowRuleSchema
from audit_workbench.services.run_enqueue import RunSnapshot
from audit_workbench.services.run_service import FileBinding
from audit_workbench.services.run_upload_bindings import parse_json_form
from audit_workbench.services.upload_intents import UploadIntentError, bindings_from_confirmed_uploads
from audit_workbench.util.json_shape import normalize_keys_to_snake


async def bindings_from_stored(
    session: AsyncSession,
    stored: list[StoredFileBinding],
    *,
    authorization: str | None,
) -> list[FileBinding]:
    requested = [
        FileBinding(
            document_id=item.document_id,
            storage_key=item.storage_key,
            mime_type=item.mime_type,
            file_name=item.file_name,
        )
        for item in stored
    ]
    try:
        return await bindings_from_confirmed_uploads(
            session,
            requested,
            owner_subject=resolve_owner_subject(authorization),
        )
    except UploadIntentError as exc:
        raise HTTPException(400, str(exc)) from exc


def snapshot_from_body(body: RunSnapshotBody | None) -> RunSnapshot | None:
    if not body:
        return None
    return RunSnapshot(
        documents=body.documents,
        rules=body.rules,
        workflow_name=body.workflow_name,
    )


def snapshot_from_form_payload(payload: str | None) -> RunSnapshot | None:
    if not payload:
        return None
    data = parse_json_form(payload, "payload")
    if not isinstance(data, dict):
        raise HTTPException(400, "Invalid JSON in payload — expected an object.")
    data = normalize_keys_to_snake(data)
    return RunSnapshot(
        documents=[DocumentDefSchema.model_validate(d) for d in data.get("documents", [])],
        rules=[WorkflowRuleSchema.model_validate(r) for r in data.get("rules", [])],
        workflow_name=data.get("workflow_name"),
    )
