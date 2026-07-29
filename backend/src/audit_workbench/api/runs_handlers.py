"""Run route helpers — multipart/JSON binding and snapshot parsing."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.api.errors import raise_app_error
from audit_workbench.infra.auth.run_access import resolve_owner_subject
from audit_workbench.runtime.run.contracts import FileBinding, RunSnapshot
from audit_workbench.schemas.run_requests import RunSnapshotBody, StoredFileBinding
from audit_workbench.schemas.workflow import DocumentDefSchema, WorkflowRuleSchema
from audit_workbench.app.run.upload_bindings import parse_json_form
from audit_workbench.app.uploads.intents import bindings_from_confirmed_uploads
from audit_workbench.util.json_shape import normalize_keys_to_snake


async def bindings_from_stored(
    session: AsyncSession,
    stored: list[StoredFileBinding],
    *,
    authorization: str | None,
) -> list[FileBinding]:
    result = await bindings_from_confirmed_uploads(
        session,
        [item.to_binding() for item in stored],
        owner_subject=resolve_owner_subject(authorization),
    )
    if not result.is_ok:
        assert result.error is not None
        raise_app_error(result.error)
    return result.unwrap()


def snapshot_from_body(body: RunSnapshotBody | None) -> RunSnapshot | None:
    return body.to_snapshot() if body else None


def snapshot_from_form_payload(payload: str | None) -> RunSnapshot | None:
    if not payload:
        return None
    data_r = parse_json_form(payload, "payload")
    if not data_r.is_ok:
        assert data_r.error is not None
        raise_app_error(data_r.error)
    data = data_r.unwrap()
    if not isinstance(data, dict):
        raise HTTPException(400, "Invalid JSON in payload — expected an object.")
    data = normalize_keys_to_snake(data)
    return RunSnapshot(
        documents=[DocumentDefSchema.model_validate(d) for d in data.get("documents", [])],
        rules=[WorkflowRuleSchema.model_validate(r) for r in data.get("rules", [])],
        workflow_name=data.get("workflow_name"),
    )
