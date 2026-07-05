"""Deep Run enqueue module — admission, create, dispatch policy."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import structlog
from asgi_correlation_id import correlation_id
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.auth.dependencies import extract_bearer
from audit_workbench.auth.run_access import RunSource, resolve_run_enqueue_source
from audit_workbench.schemas.workflow import (
    DocumentDefSchema,
    RunCreatedResponse,
    WorkflowRuleSchema,
)
from audit_workbench.services import run_service
from audit_workbench.services.admission import QueueCapacityExceeded, check_admission
from audit_workbench.services.dispatch_outbox import enqueue_dispatch, schedule_outbox_dispatch
from audit_workbench.services.queue import refresh_queued_positions
from audit_workbench.services.rate_limit import RunRateLimitExceeded, check_run_rate_limits
from audit_workbench.services.run_enqueue_errors import WorkflowNotDeployedError
from audit_workbench.services.run_service import FileBinding

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class RunSnapshot:
    documents: list[DocumentDefSchema]
    rules: list[WorkflowRuleSchema]
    workflow_name: str | None = None


@dataclass(frozen=True)
class EnqueueRunRequest:
    workflow_id: str
    authorization: str | None = None
    file_bindings: list[FileBinding] | None = None
    snapshot: RunSnapshot | None = None
    client_host: str | None = None
    """True for bare POST /runs (production API shape without builder snapshot)."""
    production_api_shape: bool = False


def client_key_from_request(
    source: str, authorization: str | None, client_host: str | None
) -> str | None:
    if source == "api" and authorization:
        token = extract_bearer(authorization)
        if token:
            return hashlib.sha256(token.encode()).hexdigest()[:16]
    return client_host


async def enqueue_run(
    session: AsyncSession,
    req: EnqueueRunRequest,
) -> RunCreatedResponse:
    """Create and queue a Run — single interface for all HTTP entry shapes."""
    source, wf = await resolve_run_enqueue_source(
        session,
        req.workflow_id,
        req.authorization,
        has_snapshot=req.snapshot is not None,
        production_api_shape=req.production_api_shape,
    )
    client_key = client_key_from_request(source, req.authorization, req.client_host)

    if source == "api" and not wf.deployed_at:
        raise WorkflowNotDeployedError

    try:
        await check_run_rate_limits(
            workflow_id=req.workflow_id,
            source=source,
            client_key=client_key,
        )
    except RunRateLimitExceeded:
        raise

    try:
        predicted_pool = await check_admission(
            session,
            workflow_id=req.workflow_id,
            file_bindings=req.file_bindings,
        )
    except QueueCapacityExceeded:
        raise

    snapshot = req.snapshot if source == "test" else None
    run = await run_service.create_run(
        session,
        req.workflow_id,
        source=source,
        file_bindings=req.file_bindings,
        snapshot_documents=snapshot.documents if snapshot else None,
        snapshot_rules=snapshot.rules if snapshot else None,
        snapshot_workflow_name=snapshot.workflow_name if snapshot else None,
        worker_pool=predicted_pool,
    )

    request_id = correlation_id.get()

    await enqueue_dispatch(
        session,
        run_id=run.id,
        pool=predicted_pool,
        workflow_id=req.workflow_id,
        request_id=request_id,
    )
    await refresh_queued_positions(session)
    await session.commit()
    schedule_outbox_dispatch(run.id)
    return RunCreatedResponse(run_id=run.id, job_id=run.id, status=run.status)
