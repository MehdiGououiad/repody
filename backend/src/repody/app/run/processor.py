from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime

import structlog
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from repody.agents.idp.run import execute_idp_run
from repody.app.run.commands import (
    PUBLIC_RUN_FAILURE_MESSAGE,
    ClaimRunRequest,
    claim_run,
    fail_run_terminal,
    publish_run_domain_events,
)
from repody.app.run.persistence import bind_try_claim
from repody.infra.db.models import (
    Document,
    ExtractedField,
    RuleResult,
    Run,
    RunDocument,
    RunStatus,
    Workflow,
)
from repody.settings import get_settings

log = structlog.get_logger()


def advisory_lock_key(run_id: str) -> int:
    """Deterministic int64 key for pg_advisory_xact_lock (stable across processes)."""
    digest = hashlib.sha256(run_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") & 0x7FFFFFFFFFFFFFFF


async def execute_run_with_timeout(
    run_id: str,
    *,
    request_id: str | None = None,
    session: AsyncSession | None = None,
) -> None:
    """Process one run with a hard ceiling from AUDIT_WORKER_TASK_TIMEOUT_MINUTES.

    When ``session`` is omitted (workers), process_run opens a managed session and
    commits after claim so IDP extract ports can use separate short-lived connections.
    Tests may pass a shared ``session``.
    """
    settings = get_settings()
    timeout_seconds = settings.worker_task_timeout_minutes * 60
    try:
        await asyncio.wait_for(
            process_run(session, run_id, request_id=request_id),
            timeout=timeout_seconds,
        )
    except TimeoutError:
        if session is not None:
            await session.rollback()
        minutes = settings.worker_task_timeout_minutes
        await fail_run_terminal(
            run_id,
            f"Run exceeded {minutes} minute task timeout",
            expected_status=RunStatus.running.value,
        )
        raise


async def _try_advisory_lock(session: AsyncSession, run_id: str) -> bool:
    bind = session.get_bind()
    if bind.dialect.name != "postgresql":
        return True
    lock_key = advisory_lock_key(run_id)
    result = await session.execute(
        text("SELECT pg_try_advisory_xact_lock(:key)"),
        {"key": lock_key},
    )
    return bool(result.scalar())


async def _clear_prior_run_results(session: AsyncSession, run_id: str) -> None:
    await session.execute(delete(RuleResult).where(RuleResult.run_id == run_id))
    rd_result = await session.execute(select(RunDocument.id).where(RunDocument.run_id == run_id))
    rd_ids = list(rd_result.scalars())
    if rd_ids:
        await session.execute(
            delete(ExtractedField).where(ExtractedField.run_document_id.in_(rd_ids))
        )


async def _load_run_graph(session: AsyncSession, run_id: str) -> Run | None:
    result = await session.execute(
        select(Run)
        .where(Run.id == run_id)
        .options(
            selectinload(Run.documents).selectinload(RunDocument.fields),
            selectinload(Run.workflow)
            .selectinload(Workflow.documents)
            .selectinload(Document.schema_fields),
            selectinload(Run.workflow).selectinload(Workflow.rules),
        )
    )
    return result.scalar_one_or_none()


async def _touch_run_activity(session: AsyncSession, run: Run) -> None:
    run.last_activity_at = datetime.now(UTC)
    await session.flush()


async def _claim_run(session: AsyncSession, run_id: str) -> Run | None:
    """CAS queued -> running; skip if already running or finished."""
    if not await _try_advisory_lock(session, run_id):
        log.info(
            "run_claim_lock_busy",
            event_domain="audit_run",
            run_id=run_id,
        )
        return None

    now = datetime.now(UTC)
    claim_result = await claim_run(
        ClaimRunRequest(run_id=run_id),
        try_claim=bind_try_claim(session),
        now=now,
    )
    if claim_result is None:
        run = await session.get(Run, run_id)
        if run:
            log.info(
                "run_claim_skipped",
                event_domain="audit_run",
                run_id=run_id,
                run_status=run.status,
            )
        return None

    await _clear_prior_run_results(session, run_id)
    await session.commit()

    await publish_run_domain_events(claim_result.events)
    return await _load_run_graph(session, run_id)


async def _persist_run_failure(run_id: str, exc: Exception) -> None:
    await fail_run_terminal(run_id, PUBLIC_RUN_FAILURE_MESSAGE)
    log.error(
        "run_failed",
        event_domain="audit_run",
        run_id=run_id,
        error_type=type(exc).__name__,
        error_message=repr(exc),
        exc_info=exc,
    )


async def process_run(
    session: AsyncSession | None,
    run_id: str,
    *,
    request_id: str | None = None,
) -> None:
    """Claim the run and execute it through the IDP agent.

    Workers pass ``session=None``; a short-lived session is opened and committed after
    claim so IDP extract ports can use separate connections without row-lock deadlocks.
    Tests may pass a shared ``session``.
    """
    if session is not None:
        await _process_run_with_session(session, run_id, request_id=request_id)
        return

    from repody.infra.db.base import async_session_factory

    async with async_session_factory() as managed:
        await _process_run_with_session(managed, run_id, request_id=request_id)


async def _process_run_with_session(
    session: AsyncSession,
    run_id: str,
    *,
    request_id: str | None,
) -> None:
    log.info(
        "run_processing_started",
        event_domain="audit_run",
        run_id=run_id,
        # Workers run outside the ASGI correlation-id middleware, so the
        # originating request is carried on the task and logged here.
        request_id=request_id,
    )
    run = await _claim_run(session, run_id)
    if run is None:
        return

    try:
        await _touch_run_activity(session, run)
        await session.commit()

        run = await _load_run_graph(session, run_id)
        if run is None:
            return

        # execute_idp_run persists results and completes the run itself.
        result = await execute_idp_run(session, run)
        if not result.is_ok:
            raise RuntimeError(result.error.message if result.error else "IDP run failed")
    except Exception as exc:
        await session.rollback()
        await _persist_run_failure(run_id, exc)
        raise
