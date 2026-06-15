from __future__ import annotations

import json

import structlog
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from audit_workbench.api.auth import require_admin, require_admin_or_workflow_run, require_test_run_admin
from audit_workbench.api.deps import get_session
from audit_workbench.schemas.common import CamelModel
from audit_workbench.schemas.workflow import (
    DocumentDefSchema,
    RunCreatedResponse,
    RunPollResponse,
    WorkflowRuleSchema,
)
from audit_workbench.services import run_service
from audit_workbench.services.run_enqueue import EnqueueRunRequest, RunSnapshot, client_key_from_request, enqueue_run
from audit_workbench.services.run_events import subscribe_run_progress
from audit_workbench.services.run_service import FileBinding
from audit_workbench.db.models import Run
from audit_workbench.services.run_upload_bindings import bindings_from_multipart, parse_json_form

router = APIRouter(tags=["runs"])
log = structlog.get_logger(__name__)


class RunSnapshotBody(BaseModel):
    """Ephemeral workflow config for this run only — does not mutate the saved workflow."""

    documents: list[DocumentDefSchema] = []
    rules: list[WorkflowRuleSchema] = []
    workflow_name: str | None = None


class StoredFileBinding(CamelModel):
    document_id: str | None = None
    storage_key: str
    mime_type: str
    file_name: str


class CreateRunJsonBody(CamelModel):
    snapshot: RunSnapshotBody | None = None
    payload: RunSnapshotBody | None = None  # legacy alias
    file_bindings: list[StoredFileBinding] = []


@router.get("/runs/{run_id}/status")
async def get_run_status(
    run_id: str,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin_or_workflow_run),
):
    """Lightweight poll — status + progress only (no full audit payload)."""
    return await run_service.poll_run_status(session, run_id)


@router.get("/runs/{run_id}", response_model=RunPollResponse)
async def get_run(
    run_id: str,
    session: AsyncSession = Depends(get_session),
    full: bool = Query(True, description="If false, same as /status (lightweight)."),
    _: None = Depends(require_admin_or_workflow_run),
):
    if not full:
        body = await run_service.poll_run_status(session, run_id)
        return RunPollResponse(
            status=body["status"],
            progress=body.get("progress"),
            result=None,
            error=body.get("error"),
        )
    status, result, error, progress = await run_service.poll_run(session, run_id)
    return RunPollResponse(status=status, progress=progress, result=result, error=error)


@router.get("/runs/{run_id}/events")
async def stream_run_events(
    run_id: str,
    _: None = Depends(require_admin_or_workflow_run),
):
    """Server-Sent Events stream for live run progress (Redis pub/sub)."""
    from audit_workbench.db import base as db_base

    async with db_base.async_session_factory() as session:
        run = await session.get(Run, run_id)
        if not run:
            raise HTTPException(404, "Run not found")
        initial_progress = run.progress

    async def event_generator():
        if initial_progress:
            yield {
                "data": json.dumps(
                    {"runId": run_id, "progress": initial_progress},
                    ensure_ascii=False,
                )
            }
        async for payload in subscribe_run_progress(run_id):
            yield {"data": json.dumps(payload, ensure_ascii=False)}

    log.info(
        "run_events_stream_started",
        event_domain="run_events",
        run_id=run_id,
    )
    return EventSourceResponse(
        event_generator(),
        ping=30,
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


def _bindings_from_stored(stored: list[StoredFileBinding]) -> list[FileBinding]:
    return [
        FileBinding(
            document_id=item.document_id,
            storage_key=item.storage_key,
            mime_type=item.mime_type,
            file_name=item.file_name,
        )
        for item in stored
    ]


def _snapshot_from_body(body: RunSnapshotBody | None) -> RunSnapshot | None:
    if not body:
        return None
    return RunSnapshot(
        documents=body.documents,
        rules=body.rules,
        workflow_name=body.workflow_name,
    )


def _snapshot_from_legacy_payload(payload: str | None) -> RunSnapshot | None:
    if not payload:
        return None
    data = parse_json_form(payload, "payload")
    if not isinstance(data, dict):
        raise HTTPException(400, "Invalid JSON in payload — expected an object.")
    return RunSnapshot(
        documents=[DocumentDefSchema.model_validate(d) for d in data.get("documents", [])],
        rules=[WorkflowRuleSchema.model_validate(r) for r in data.get("rules", [])],
        workflow_name=data.get("workflowName") or data.get("workflow_name"),
    )


@router.post(
    "/workflows/{workflow_id}/runs/json",
    response_model=RunCreatedResponse | RunPollResponse,
    status_code=202,
)
async def create_run_json(
    workflow_id: str,
    body: CreateRunJsonBody,
    request: Request,
    mode: str | None = Query(None),
    inline: bool = Query(False, description="Process synchronously (test/dev only)."),
    authorization: str | None = Header(None),
    session: AsyncSession = Depends(get_session),
    __admin: None = Depends(require_test_run_admin),
):
    """Create a run with files already uploaded to storage (presigned PUT flow)."""
    source = "test" if mode == "test" else "api"
    bindings = _bindings_from_stored(body.file_bindings) if body.file_bindings else None
    snapshot = _snapshot_from_body(body.snapshot or body.payload)
    return await enqueue_run(
        session,
        EnqueueRunRequest(
            workflow_id=workflow_id,
            source=source,
            authorization=authorization,
            file_bindings=bindings,
            snapshot=snapshot,
            client_key=client_key_from_request(source, authorization, request),
            inline=inline,
        ),
    )


@router.post(
    "/workflows/{workflow_id}/runs",
    response_model=RunCreatedResponse | RunPollResponse,
    status_code=202,
)
async def create_run(
    workflow_id: str,
    request: Request,
    mode: str | None = Query(None),
    inline: bool = Query(False, description="Process synchronously (test/dev only)."),
    authorization: str | None = Header(None),
    session: AsyncSession = Depends(get_session),
    files: list[UploadFile] | None = File(None),
    document_ids: str | None = Form(None),
    document_types: str | None = Form(
        None,
        description="JSON array of configured document type names, same order as files.",
    ),
    payload: str | None = Form(None),
    __admin: None = Depends(require_test_run_admin),
):
    source = "test" if mode == "test" else "api"
    bindings: list[FileBinding] | None = None
    snapshot = _snapshot_from_legacy_payload(payload)
    if files:
        bindings = await bindings_from_multipart(
            session,
            workflow_id,
            files,
            document_ids=document_ids,
            document_types=document_types,
        )
    return await enqueue_run(
        session,
        EnqueueRunRequest(
            workflow_id=workflow_id,
            source=source,
            authorization=authorization,
            file_bindings=bindings,
            snapshot=snapshot,
            client_key=client_key_from_request(source, authorization, request),
            inline=inline,
        ),
    )


@router.post(
    "/workflows/{workflow_id}/run",
    response_model=RunCreatedResponse,
    status_code=202,
    deprecated=True,
)
async def create_run_legacy(
    workflow_id: str,
    request: Request,
    authorization: str | None = Header(None),
    session: AsyncSession = Depends(get_session),
    files: list[UploadFile] | None = File(None),
    document_ids: str | None = Form(None),
    document_types: str | None = Form(None),
):
    bindings = None
    if files:
        bindings = await bindings_from_multipart(
            session,
            workflow_id,
            files,
            document_ids=document_ids,
            document_types=document_types,
        )
    return await enqueue_run(
        session,
        EnqueueRunRequest(
            workflow_id=workflow_id,
            source="api",
            authorization=authorization,
            file_bindings=bindings,
            client_key=client_key_from_request("api", authorization, request),
        ),
    )


@router.post(
    "/workflows/{workflow_id}/test-run",
    response_model=RunCreatedResponse,
    status_code=202,
    deprecated=True,
)
async def test_run(
    workflow_id: str,
    body: RunSnapshotBody,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin),
):
    """Deprecated — use POST /runs/json?mode=test and poll GET /runs/{id}."""
    response = await enqueue_run(
        session,
        EnqueueRunRequest(
            workflow_id=workflow_id,
            source="test",
            snapshot=_snapshot_from_body(body),
        ),
    )
    if isinstance(response, RunCreatedResponse):
        return response
    raise HTTPException(500, "Unexpected synchronous test-run response")
