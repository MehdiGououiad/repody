"""Deep Run enqueue module — admission, create, dispatch policy."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import structlog
from asgi_correlation_id import correlation_id
from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.api.auth import extract_bearer
from audit_workbench.schemas.workflow import DocumentDefSchema, RunCreatedResponse, RunPollResponse, WorkflowRuleSchema
from audit_workbench.services import run_service
from audit_workbench.services.admission import QueueCapacityExceeded, check_admission, refresh_queued_positions
from audit_workbench.services.api_keys import verify_api_key
from audit_workbench.services.dispatch_outbox import dispatch_outbox_row, enqueue_dispatch
from audit_workbench.services.mappers import load_workflow
from audit_workbench.services.rate_limit import RateLimitExceeded, check_run_rate_limits
from audit_workbench.db.models import RunDispatchOutbox
from audit_workbench.services.run_service import FileBinding, progress_from_run
from audit_workbench.settings import get_settings

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class RunSnapshot:
    documents: list[DocumentDefSchema]
    rules: list[WorkflowRuleSchema]
    workflow_name: str | None = None


@dataclass(frozen=True)
class EnqueueRunRequest:
    workflow_id: str
    source: str
    authorization: str | None = None
    file_bindings: list[FileBinding] | None = None
    snapshot: RunSnapshot | None = None
    client_key: str | None = None
    inline: bool = False


def client_key_from_request(source: str, authorization: str | None, request: Request | None) -> str | None:
    if source == "api" and authorization:
        token = authorization.replace("Bearer ", "").strip()
        if token:
            return hashlib.sha256(token.encode()).hexdigest()[:16]
    if request and request.client:
        return request.client.host
    return None


async def enqueue_run(
    session: AsyncSession,
    req: EnqueueRunRequest,
) -> RunCreatedResponse | RunPollResponse:
    """Create and queue a Run — single interface for all HTTP entry shapes."""
    try:
        await check_run_rate_limits(
            workflow_id=req.workflow_id,
            source=req.source,
            client_key=req.client_key,
        )
    except RateLimitExceeded as exc:
        raise HTTPException(429, str(exc)) from exc

    try:
        predicted_pool = await check_admission(
            session,
            workflow_id=req.workflow_id,
            file_bindings=req.file_bindings,
        )
    except QueueCapacityExceeded as exc:
        raise HTTPException(
            503,
            str(exc),
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc

    wf = await load_workflow(session, req.workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow not found")

    if req.source == "api":
        if not wf.deployed_at:
            raise HTTPException(409, "Workflow is not deployed.")
        token = extract_bearer(req.authorization)
        if not token or not verify_api_key(token, wf.api_key):
            log.warning(
                "run_create_unauthorized",
                event_domain="audit_run",
                workflow_id=req.workflow_id,
                source=req.source,
            )
            raise HTTPException(401, "Invalid API key.")

    inline = req.inline
    if req.source == "test":
        inline = False

    snapshot = req.snapshot
    run = await run_service.create_run(
        session,
        req.workflow_id,
        source=req.source,
        file_bindings=req.file_bindings,
        snapshot_documents=snapshot.documents if snapshot else None,
        snapshot_rules=snapshot.rules if snapshot else None,
        snapshot_workflow_name=snapshot.workflow_name if snapshot else None,
        force_inline=inline,
        worker_pool=predicted_pool,
    )

    settings = get_settings()
    request_id = correlation_id.get()

    if not settings.run_jobs_inline and not inline:
        await enqueue_dispatch(
            session,
            run_id=run.id,
            pool=predicted_pool,
            workflow_id=req.workflow_id,
            request_id=request_id,
        )
        await session.commit()

        row = await session.get(RunDispatchOutbox, run.id)
        if row is None:
            raise HTTPException(503, "Failed to enqueue audit run")
        ok = await dispatch_outbox_row(session, row)
        if not ok:
            raise HTTPException(503, "Failed to enqueue audit run")
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
