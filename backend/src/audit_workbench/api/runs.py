from __future__ import annotations

import hashlib
import json
import uuid

import structlog
from asgi_correlation_id import correlation_id
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from audit_workbench.api.auth import (
    extract_bearer,
    require_admin,
    require_admin_or_workflow_run,
    require_test_run_admin,
)
from audit_workbench.api.deps import get_session
from audit_workbench.db.models import Run
from audit_workbench.schemas.run import RunAuditDetail
from audit_workbench.schemas.workflow import (
    DocumentDefSchema,
    RunCreatedResponse,
    RunPollResponse,
    RunProgressSchema,
    WorkflowRuleSchema,
)
from audit_workbench.schemas.common import CamelModel
from audit_workbench.services import run_service
from audit_workbench.services.api_keys import verify_api_key
from audit_workbench.services.mappers import load_workflow
from audit_workbench.services.run_service import FileBinding, progress_from_run
from audit_workbench.services.upload_validation import UploadValidationError, validate_upload_batch, validate_upload_file
from audit_workbench.services.run_dispatch import dispatch_audit_run, mark_run_dispatch_failed
from audit_workbench.services.worker_pool import resolve_worker_pool
from audit_workbench.services.rate_limit import RateLimitExceeded, check_run_rate_limits
from audit_workbench.services.admission import QueueCapacityExceeded, check_admission, refresh_queued_positions
from audit_workbench.services.run_events import subscribe_run_progress
from audit_workbench.settings import get_settings
from audit_workbench.storage.factory import get_storage

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


async def _enqueue_run(
    workflow_id: str,
    source: str,
    authorization: str | None,
    session: AsyncSession,
    *,
    file_bindings: list[FileBinding] | None = None,
    snapshot: RunSnapshotBody | None = None,
    client_key: str | None = None,
    inline: bool = False,
) -> RunCreatedResponse | RunPollResponse:
    try:
        await check_run_rate_limits(
            workflow_id=workflow_id,
            source=source,
            client_key=client_key,
        )
    except RateLimitExceeded as exc:
        raise HTTPException(429, str(exc)) from exc

    try:
        predicted_pool = await check_admission(
            session,
            workflow_id=workflow_id,
            file_bindings=file_bindings,
        )
    except QueueCapacityExceeded as exc:
        raise HTTPException(
            503,
            str(exc),
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc

    wf = await load_workflow(session, workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow not found")

    if source == "api":
        if not wf.deployed_at:
            raise HTTPException(409, "Workflow is not deployed.")
        token = extract_bearer(authorization)
        if not token or not verify_api_key(token, wf.api_key):
            log.warning(
                "run_create_unauthorized",
                event_domain="audit_run",
                workflow_id=workflow_id,
                source=source,
            )
            raise HTTPException(401, "Invalid API key.")

    run = await run_service.create_run(
        session,
        workflow_id,
        source=source,
        file_bindings=file_bindings,
        snapshot_documents=snapshot.documents if snapshot else None,
        snapshot_rules=snapshot.rules if snapshot else None,
        snapshot_workflow_name=snapshot.workflow_name if snapshot else None,
        force_inline=inline,
    )

    settings = get_settings()
    if not settings.run_jobs_inline and not inline:
        pool = predicted_pool
        await session.commit()
        try:
            await dispatch_audit_run(
                run.id,
                pool=pool,
                workflow_id=workflow_id,
                request_id=correlation_id.get(),
            )
        except Exception as exc:
            await mark_run_dispatch_failed(run.id, exc)
            raise HTTPException(503, "Failed to enqueue audit run") from exc
        await refresh_queued_positions(session)
        await session.commit()
        return RunCreatedResponse(run_id=run.id, job_id=run.id, status=run.status)

    await session.commit()
    if inline:
        await session.refresh(run)
        detail = await run_service.get_run_detail(session, run.id)
        if not detail:
            raise HTTPException(500, "Run failed")
        return RunPollResponse(
            status=run.status,
            progress=progress_from_run(run),
            result=detail,
            error=run.error,
        )
    return RunCreatedResponse(run_id=run.id, job_id=run.id, status=run.status)


def _client_key(source: str, authorization: str | None, request: Request | None) -> str | None:
    if source == "api" and authorization:
        token = authorization.replace("Bearer ", "").strip()
        if token:
            return hashlib.sha256(token.encode()).hexdigest()[:16]
    if request and request.client:
        return request.client.host
    return None


async def _bindings_from_uploads(
    files: list[UploadFile],
    document_ids: list[str] | None,
) -> list[FileBinding]:
    settings = get_settings()
    validate_upload_batch(file_count=len(files), settings=settings)
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
            raise HTTPException(400, str(exc)) from exc

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
    return bindings


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


def _parse_json_form(value: str | None, field_name: str) -> list | dict | None:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, f"Invalid JSON in {field_name}.") from exc


def _snapshot_from_legacy_payload(payload: str | None) -> RunSnapshotBody | None:
    if not payload:
        return None
    data = _parse_json_form(payload, "payload")
    if not isinstance(data, dict):
        raise HTTPException(400, "Invalid JSON in payload — expected an object.")
    return RunSnapshotBody(
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
    snapshot = body.snapshot or body.payload
    return await _enqueue_run(
        workflow_id,
        source,
        authorization,
        session,
        file_bindings=bindings,
        snapshot=snapshot,
        client_key=_client_key(source, authorization, request),
        inline=inline,
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
    payload: str | None = Form(None),
    __admin: None = Depends(require_test_run_admin),
):
    source = "test" if mode == "test" else "api"
    bindings: list[FileBinding] | None = None
    snapshot = _snapshot_from_legacy_payload(payload)
    if files:
        parsed_ids = _parse_json_form(document_ids, "document_ids")
        if parsed_ids is not None and not isinstance(parsed_ids, list):
            raise HTTPException(400, "Invalid JSON in document_ids — expected an array.")
        bindings = await _bindings_from_uploads(files, parsed_ids)
    return await _enqueue_run(
        workflow_id,
        source,
        authorization,
        session,
        file_bindings=bindings,
        snapshot=snapshot,
        client_key=_client_key(source, authorization, request),
        inline=inline,
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
):
    bindings = None
    if files:
        parsed_ids = _parse_json_form(document_ids, "document_ids")
        if parsed_ids is not None and not isinstance(parsed_ids, list):
            raise HTTPException(400, "Invalid JSON in document_ids — expected an array.")
        bindings = await _bindings_from_uploads(files, parsed_ids)
    result = await _enqueue_run(
        workflow_id,
        "api",
        authorization,
        session,
        file_bindings=bindings,
        client_key=_client_key("api", authorization, request),
    )
    return result


@router.post(
    "/workflows/{workflow_id}/test-run",
    deprecated=True,
)
async def test_run(
    workflow_id: str,
    body: RunSnapshotBody,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin),
):
    """Deprecated — use POST /runs/json?mode=test&inline=true."""
    response = await _enqueue_run(
        workflow_id,
        "test",
        None,
        session,
        snapshot=body,
        inline=True,
    )
    if isinstance(response, RunPollResponse):
        if response.result:
            payload = response.result.model_dump(by_alias=True)
            return {**payload, "processedAt": response.result.created_at}
    raise HTTPException(500, "Run failed")
