"""Enqueue a run: access, limits, admission, insert, then send to Taskiq."""

from __future__ import annotations

import hashlib

import structlog
from asgi_correlation_id import correlation_id
from sqlalchemy.ext.asyncio import AsyncSession

from repody.app.queue.progress import refresh_single_queued_run
from repody.app.run.access import resolve_run_enqueue_source
from repody.app.run.admission import check_admission
from repody.app.run.dispatch import dispatch_audit_run
from repody.app.run.intake import create_run
from repody.app.run.pool import predict_worker_pool
from repody.infra.auth.jwt_validator import extract_bearer
from repody.infra.rate_limit import check_run_rate_limits
from repody.runtime.contracts.result import AppError, ErrorCode
from repody.runtime.run.contracts import EnqueueRunRequest
from repody.schemas.workflow import RunCreatedResponse

log = structlog.get_logger(__name__)


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
    """Create and queue a run; raises AppError when it is refused."""
    source, wf = await resolve_run_enqueue_source(
        session,
        req.workflow_id,
        req.authorization,
        has_snapshot=req.snapshot is not None,
        production_api_shape=req.production_api_shape,
    )
    client_key = client_key_from_request(source, req.authorization, req.client_host)

    if source == "api" and not wf.deployed_at:
        raise AppError(ErrorCode.CONFLICT, "Workflow is not deployed.")

    await check_run_rate_limits(
        workflow_id=req.workflow_id,
        source=source,
        client_key=client_key,
    )

    # Reuse workflow already loaded for access - avoid a second documents query.
    predicted_pool = await predict_worker_pool(
        session,
        req.workflow_id,
        file_bindings=req.file_bindings,
        workflow=wf,
    )

    await check_admission(session, predicted_pool=predicted_pool)

    snapshot = req.snapshot if source == "test" else None
    run = await create_run(
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

    # O(1) position for the new run only - full queue refresh happens on claim.
    await refresh_single_queued_run(session, run.id)
    await session.commit()
    # After commit: a failed send leaves the run undispatched for maintenance to re-send.
    await dispatch_audit_run(
        run.id, pool=predicted_pool, workflow_id=req.workflow_id, request_id=request_id
    )
    return RunCreatedResponse(run_id=run.id, job_id=run.id, status=run.status)
