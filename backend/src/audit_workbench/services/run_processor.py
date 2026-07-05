from __future__ import annotations

import asyncio

import structlog
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from audit_workbench.db.models import (
    Document,
    ExtractedField,
    RuleResult,
    Run,
    RunDocument,
    RunStatus,
    Workflow,
)
from audit_workbench.services.run.adapters.composition import get_claim_run, get_run_publisher, run_claim_store
from audit_workbench.services.run.application.use_cases import ClaimRunRequest
from audit_workbench.services.run.extraction import run_extraction_phase
from audit_workbench.services.run.phase_state import build_phase_state
from audit_workbench.services.run.validation import run_validation_phase
from audit_workbench.services.run_lock import advisory_lock_key
from audit_workbench.services.run_terminal import PUBLIC_RUN_FAILURE_MESSAGE, fail_run_terminal
from audit_workbench.settings import get_settings

log = structlog.get_logger()


async def execute_run_with_timeout(session: AsyncSession, run_id: str) -> None:
    """Run extract+validate with a hard ceiling from AUDIT_WORKER_TASK_TIMEOUT_MINUTES."""
    settings = get_settings()
    timeout_seconds = settings.worker_task_timeout_minutes * 60
    try:
        await asyncio.wait_for(process_run(session, run_id), timeout=timeout_seconds)
    except TimeoutError:
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


async def _claim_run(session: AsyncSession, run_id: str) -> Run | None:
    """CAS queued→running; skip if already running or finished."""
    from datetime import UTC, datetime

    if not await _try_advisory_lock(session, run_id):
        log.info(
            "run_claim_lock_busy",
            event_domain="audit_run",
            run_id=run_id,
        )
        return None

    now = datetime.now(UTC)
    claim_result = await get_claim_run().execute(
        ClaimRunRequest(run_id=run_id),
        claim_store=run_claim_store(session),
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

    await get_run_publisher().publish(claim_result.events)

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


async def _persist_run_failure(run_id: str, exc: Exception) -> None:
    await fail_run_terminal(run_id, PUBLIC_RUN_FAILURE_MESSAGE)
    log.exception(
        "run_failed",
        event_domain="audit_run",
        run_id=run_id,
        error_type=type(exc).__name__,
        error_message=repr(exc),
    )


async def process_run(session: AsyncSession, run_id: str) -> None:
    """Single-worker audit pipeline: extract documents then validate rules."""
    log.info("run_processing_started", event_domain="audit_run", run_id=run_id)
    run = await _claim_run(session, run_id)
    if not run:
        return

    try:
        state = build_phase_state(run)
        await run_extraction_phase(session, state)
        await run_validation_phase(session, state)
    except Exception as exc:
        await session.rollback()
        await _persist_run_failure(run_id, exc)
        raise
