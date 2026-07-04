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
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from audit_workbench.api.deps import get_session
from audit_workbench.auth.dependencies import (
    require_admin_or_workflow_run,
    require_run_create_access,
)
from audit_workbench.db.models import Run
from audit_workbench.schemas.run_requests import CreateRunJsonBody
from audit_workbench.schemas.workflow import RunCreatedResponse, RunPollResponse
from audit_workbench.api.runs_handlers import (
    bindings_from_stored,
    snapshot_from_body,
    snapshot_from_form_payload,
)
from audit_workbench.services import run_service
from audit_workbench.services.run_enqueue import EnqueueRunRequest
from audit_workbench.api.run_enqueue_http import enqueue_run_http
from audit_workbench.services.run_events import subscribe_run_progress
from audit_workbench.services.run_service import FileBinding
from audit_workbench.services.run_upload_bindings import bindings_from_multipart

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


@router.get("/runs/{run_id}/status", response_model=RunPollResponse)
async def get_run_status(
    run_id: str,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin_or_workflow_run),
) -> RunPollResponse:
    """Lightweight poll — status and progress only (no full audit payload)."""
    body = await run_service.poll_run_status(session, run_id)
    return RunPollResponse(
        status=body.status,
        progress=body.progress,
        result=None,
        error=body.error,
    )


@router.get("/runs/{run_id}", response_model=RunPollResponse)
async def get_run(
    run_id: str,
    session: AsyncSession = Depends(get_session),
    full: bool = Query(True, description="If false, same as /status (lightweight)."),
    _: None = Depends(require_admin_or_workflow_run),
) -> RunPollResponse:
    if not full:
        body = await run_service.poll_run_status(session, run_id)
        return RunPollResponse(
            status=body.status,
            progress=body.progress,
            result=None,
            error=body.error,
        )
    poll = await run_service.poll_run(session, run_id)
    return RunPollResponse(
        status=poll.status,
        progress=poll.progress,
        result=poll.result,
        error=poll.error,
    )


@router.get(
    "/runs/{run_id}/events",
    responses=_RUN_EVENTS_OPENAPI,
)
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


@router.post(
    "/workflows/{workflow_id}/runs/json",
    response_model=RunCreatedResponse,
    status_code=202,
)
async def create_run_json(
    workflow_id: str,
    body: CreateRunJsonBody,
    request: Request,
    authorization: str | None = Header(None),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_run_create_access),
):
    """Create a run with files already uploaded to storage (presigned PUT flow)."""
    bindings = (
        await bindings_from_stored(
            session,
            body.file_bindings,
            authorization=authorization,
        )
        if body.file_bindings
        else None
    )
    snapshot = snapshot_from_body(body.snapshot)
    return await enqueue_run_http(
        session,
        EnqueueRunRequest(
            workflow_id=workflow_id,
            authorization=authorization,
            file_bindings=bindings,
            snapshot=snapshot,
            client_host=request.client.host if request.client else None,
            production_api_shape=False,
        ),
    )


@router.post(
    "/workflows/{workflow_id}/runs",
    response_model=RunCreatedResponse,
    status_code=202,
)
async def create_run(
    workflow_id: str,
    request: Request,
    authorization: str | None = Header(None),
    session: AsyncSession = Depends(get_session),
    files: list[UploadFile] | None = File(None),
    document_ids: str | None = Form(None),
    document_types: str | None = Form(
        None,
        description="JSON array of configured document type names, same order as files.",
    ),
    payload: str | None = Form(None),
    _: None = Depends(require_run_create_access),
):
    """Multipart fallback when presigned upload is unavailable."""
    bindings: list[FileBinding] | None = None
    snapshot = snapshot_from_form_payload(payload)
    if files:
        bindings = await bindings_from_multipart(
            session,
            workflow_id,
            files,
            document_ids=document_ids,
            document_types=document_types,
        )
    return await enqueue_run_http(
        session,
        EnqueueRunRequest(
            workflow_id=workflow_id,
            authorization=authorization,
            file_bindings=bindings,
            snapshot=snapshot,
            client_host=request.client.host if request.client else None,
            production_api_shape=snapshot is None,
        ),
    )
