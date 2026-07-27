"""Enqueue run — Result-only application boundary."""

from __future__ import annotations

import hashlib

import structlog
from asgi_correlation_id import correlation_id
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.auth.dependencies import extract_bearer
from audit_workbench.auth.run_access import resolve_run_enqueue_source
from audit_workbench.platform.contracts.result import AppError, ErrorCode, Result
from audit_workbench.platform.run.contracts import EnqueueRunRequest
from audit_workbench.schemas.workflow import RunCreatedResponse
from audit_workbench.services.dispatch_outbox import enqueue_dispatch, schedule_outbox_dispatch
from audit_workbench.services.queue import refresh_queued_positions
from audit_workbench.services.rate_limit import check_run_rate_limits
from audit_workbench.services.run.intake import create_run
from audit_workbench.services.run.pool import predict_worker_pool

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
) -> Result[RunCreatedResponse]:
    """Create and queue a Run — errors as data."""
    access = await resolve_run_enqueue_source(
        session,
        req.workflow_id,
        req.authorization,
        has_snapshot=req.snapshot is not None,
        production_api_shape=req.production_api_shape,
    )
    if not access.is_ok:
        return Result.fail(access.error or AppError(code=ErrorCode.INFRA, message="Access failed"))

    source, wf = access.unwrap()
    client_key = client_key_from_request(source, req.authorization, req.client_host)

    if source == "api" and not wf.deployed_at:
        return Result.fail(
            AppError(code=ErrorCode.CONFLICT, message="Workflow is not deployed.")
        )

    rate = await check_run_rate_limits(
        workflow_id=req.workflow_id,
        source=source,
        client_key=client_key,
    )
    if not rate.is_ok:
        return Result.fail(rate.error or AppError(code=ErrorCode.RATE_LIMIT, message="Rate limited"))

    predicted_pool = await predict_worker_pool(
        session,
        req.workflow_id,
        file_bindings=req.file_bindings,
    )

    snapshot = req.snapshot if source == "test" else None
    created = await create_run(
        session,
        req.workflow_id,
        source=source,
        file_bindings=req.file_bindings,
        snapshot_documents=snapshot.documents if snapshot else None,
        snapshot_rules=snapshot.rules if snapshot else None,
        snapshot_workflow_name=snapshot.workflow_name if snapshot else None,
        worker_pool=predicted_pool,
    )
    if not created.is_ok:
        return Result.fail(created.error or AppError(code=ErrorCode.INFRA, message="Create failed"))

    run = created.unwrap()
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
    return Result.ok(RunCreatedResponse(run_id=run.id, job_id=run.id, status=run.status))
