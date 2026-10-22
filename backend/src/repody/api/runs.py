from __future__ import annotations

import json
from typing import Any

import structlog
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from sse_starlette.sse import EventSourceResponse

from repody.api.auth import require_admin_or_workflow_run, require_run_create_access
from repody.api.deps import SessionDep
from repody.api.errors import unwrap_or_raise
from repody.api.uploads import read_upload_capped
from repody.app.run.access import resolve_owner_subject
from repody.app.run.enqueue import enqueue_run
from repody.app.run.intake import initial_run_progress, poll_run, poll_run_status
from repody.app.run.sse import subscribe_run_progress
from repody.app.run.upload_bindings import bindings_from_multipart, parse_json_form
from repody.app.uploads.intents import bindings_from_confirmed_uploads
from repody.runtime.run.contracts import EnqueueRunRequest, FileBinding, RunSnapshot
from repody.schemas.run_requests import CreateRunJsonBody
from repody.schemas.workflow import (
    DocumentDefSchema,
    RunCreatedResponse,
    RunPollResponse,
    WorkflowRuleSchema,
)
from repody.settings import get_settings
from repody.util.json_shape import normalize_keys_to_snake

router = APIRouter(tags=["runs"])
log = structlog.get_logger(__name__)

_RUN_EVENTS_OPENAPI: dict[int | str, dict[str, Any]] = {
    200: {
        "description": "Server-Sent Events stream of run progress updates",
        "content": {
            "text/event-stream": {
                "schema": {
                    "type": "string",
                    "description": "SSE `data:` frames containing JSON progress payloads",
                }
            }
        },
    }
}


def _snapshot_from_form_payload(payload: str | None) -> RunSnapshot | None:
    data = unwrap_or_raise(parse_json_form(payload, "payload"))
    if data is None:
        return None
    if not isinstance(data, dict):
        raise HTTPException(400, "Invalid JSON in payload — expected an object.")
    data = normalize_keys_to_snake(data)
    return RunSnapshot(
        documents=[DocumentDefSchema.model_validate(d) for d in data.get("documents", [])],
        rules=[WorkflowRuleSchema.model_validate(r) for r in data.get("rules", [])],
        workflow_name=data.get("workflow_name"),
    )


@router.get(
    "/runs/{run_id}/status",
    response_model=RunPollResponse,
    dependencies=[Depends(require_admin_or_workflow_run)],
)
async def get_run_status(run_id: str, session: SessionDep) -> RunPollResponse:
    """Lightweight poll - status and progress only (no full audit payload)."""
    body = await poll_run_status(session, run_id)
    return RunPollResponse(
        status=body.status,
        progress=body.progress,
        result=None,
        error=body.error,
    )


@router.get(
    "/runs/{run_id}",
    response_model=RunPollResponse,
    dependencies=[Depends(require_admin_or_workflow_run)],
)
async def get_run(
    run_id: str,
    session: SessionDep,
    full: bool = Query(True, description="If false, same as /status (lightweight)."),
) -> RunPollResponse:
    if not full:
        return await get_run_status(run_id, session)
    return await poll_run(session, run_id)


@router.get(
    "/runs/{run_id}/events",
    responses=_RUN_EVENTS_OPENAPI,
    dependencies=[Depends(require_admin_or_workflow_run)],
)
async def stream_run_events(run_id: str):
    """Server-Sent Events stream for live run progress (Redis pub/sub)."""
    initial_progress = unwrap_or_raise(await initial_run_progress(run_id))

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

    log.info("run_events_stream_started", event_domain="run_events", run_id=run_id)
    return EventSourceResponse(
        event_generator(),
        ping=30,
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post(
    "/workflows/{workflow_id}/runs/json",
    response_model=RunCreatedResponse,
    status_code=202,
    dependencies=[Depends(require_run_create_access)],
)
async def create_run_json(
    workflow_id: str,
    body: CreateRunJsonBody,
    request: Request,
    session: SessionDep,
    authorization: str | None = Header(None),
):
    """Create a run with files already uploaded to storage (presigned PUT flow)."""
    bindings: list[FileBinding] | None = None
    if body.file_bindings:
        bindings = unwrap_or_raise(
            await bindings_from_confirmed_uploads(
                session,
                [item.to_binding() for item in body.file_bindings],
                owner_subject=resolve_owner_subject(authorization),
            )
        )
    request_body = EnqueueRunRequest(
        workflow_id=workflow_id,
        authorization=authorization,
        file_bindings=bindings,
        snapshot=body.snapshot.to_snapshot() if body.snapshot else None,
        client_host=request.client.host if request.client else None,
        production_api_shape=False,
    )
    return unwrap_or_raise(await enqueue_run(session, request_body))


@router.post(
    "/workflows/{workflow_id}/runs",
    response_model=RunCreatedResponse,
    status_code=202,
    dependencies=[Depends(require_run_create_access)],
)
async def create_run(
    workflow_id: str,
    request: Request,
    session: SessionDep,
    authorization: str | None = Header(None),
    files: list[UploadFile] | None = File(None),
    document_ids: str | None = Form(None),
    document_types: str | None = Form(
        None,
        description="JSON array of configured document type names, same order as files.",
    ),
    payload: str | None = Form(None),
):
    """Multipart fallback when presigned upload is unavailable."""
    snapshot = _snapshot_from_form_payload(payload)
    bindings: list[FileBinding] | None = None
    if files:
        max_bytes = get_settings().max_upload_bytes
        incoming = [await read_upload_capped(upload, max_bytes=max_bytes) for upload in files]
        bindings = unwrap_or_raise(
            await bindings_from_multipart(
                session,
                workflow_id,
                incoming,
                document_ids=document_ids,
                document_types=document_types,
            )
        )
    request_body = EnqueueRunRequest(
        workflow_id=workflow_id,
        authorization=authorization,
        file_bindings=bindings,
        snapshot=snapshot,
        client_host=request.client.host if request.client else None,
        production_api_shape=snapshot is None,
    )
    return unwrap_or_raise(await enqueue_run(session, request_body))
