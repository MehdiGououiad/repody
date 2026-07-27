from __future__ import annotations

import asyncio
from datetime import UTC, datetime

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
from audit_workbench.platform.agent_metadata import agent_status_recorded
from audit_workbench.platform.contracts.agent import AgentId
from audit_workbench.platform.pools import parse_agent_stage
from audit_workbench.platform.recipe import (
    execute_platform_run,
    next_agent_after,
    resolve_recipe,
)
from audit_workbench.services.run.commands import ClaimRunRequest, claim_run
from audit_workbench.services.run.events import publish_run_domain_events
from audit_workbench.services.run.finalize import finalize_pending_completion
from audit_workbench.services.run.handoff import schedule_next_agent_stage
from audit_workbench.services.run.lock import advisory_lock_key
from audit_workbench.services.run.persistence import bind_try_claim
from audit_workbench.services.run.terminal import PUBLIC_RUN_FAILURE_MESSAGE, fail_run_terminal
from audit_workbench.settings import get_settings

log = structlog.get_logger()


async def execute_run_with_timeout(
    session: AsyncSession,
    run_id: str,
    *,
    agent_stage: str = "idp",
    request_id: str | None = None,
) -> None:
    """Run one platform agent stage with a hard ceiling from AUDIT_WORKER_TASK_TIMEOUT_MINUTES."""
    settings = get_settings()
    timeout_seconds = settings.worker_task_timeout_minutes * 60
    try:
        await asyncio.wait_for(
            process_run(
                session,
                run_id,
                agent_stage=agent_stage,
                request_id=request_id,
            ),
            timeout=timeout_seconds,
        )
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
    """CAS queued→running; skip if already running or finished."""
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


async def _load_running_run(session: AsyncSession, run_id: str) -> Run | None:
    """Later agent stages: require an already-running run (no re-claim)."""
    if not await _try_advisory_lock(session, run_id):
        log.info(
            "run_stage_lock_busy",
            event_domain="audit_run",
            run_id=run_id,
        )
        return None
    run = await _load_run_graph(session, run_id)
    if run is None:
        return None
    if run.status != RunStatus.running.value:
        log.info(
            "run_stage_skipped_not_running",
            event_domain="audit_run",
            run_id=run_id,
            run_status=run.status,
        )
        return None
    return run


async def _persist_run_failure(run_id: str, exc: Exception) -> None:
    await fail_run_terminal(run_id, PUBLIC_RUN_FAILURE_MESSAGE)
    log.exception(
        "run_failed",
        event_domain="audit_run",
        run_id=run_id,
        error_type=type(exc).__name__,
        error_message=repr(exc),
    )


async def _resume_after_recorded_stage(
    session: AsyncSession,
    run: Run,
    stage: AgentId,
    *,
    request_id: str | None,
) -> bool:
    """If this stage already recorded an outcome, resume handoff/finalize without re-exec.

    Returns True when the caller should exit (idempotent path handled).
    """
    if agent_status_recorded(run, stage) is None:
        return False

    log.info(
        "run_stage_already_recorded",
        event_domain="audit_run",
        run_id=run.id,
        agent_stage=stage.value,
    )
    recipe_r = resolve_recipe(get_settings())
    if not recipe_r.is_ok or recipe_r.value is None:
        return True
    recipe = recipe_r.value.agents
    next_agent = next_agent_after(recipe, stage)
    await _touch_run_activity(session, run)
    if next_agent is not None and agent_status_recorded(run, next_agent) is None:
        await schedule_next_agent_stage(
            session,
            run,
            next_agent,
            request_id=request_id,
        )
        return True
    if next_agent is None and run.status == RunStatus.running.value:
        # Final stage recorded but complete_run may have been interrupted.
        try:
            await finalize_pending_completion(session, run)
        except Exception:
            log.exception(
                "run_stage_resume_finalize_failed",
                event_domain="audit_run",
                run_id=run.id,
                agent_stage=stage.value,
            )
            raise
    return True


async def process_run(
    session: AsyncSession,
    run_id: str,
    *,
    agent_stage: str = "idp",
    request_id: str | None = None,
) -> None:
    """Platform entry: claim (IDP) or resume (later stages), run one agent, hand off."""
    stage = parse_agent_stage(agent_stage)
    log.info(
        "run_processing_started",
        event_domain="audit_run",
        run_id=run_id,
        agent_stage=stage.value,
    )

    if stage is AgentId.IDP:
        run = await _claim_run(session, run_id)
        if not run:
            # Claim lost because already running — resume handoff if IDP outcome exists.
            run = await _load_running_run(session, run_id)
            if run and await _resume_after_recorded_stage(
                session, run, stage, request_id=request_id
            ):
                return
            return
    else:
        run = await _load_running_run(session, run_id)
    if not run:
        return

    try:
        if await _resume_after_recorded_stage(session, run, stage, request_id=request_id):
            return
        await _touch_run_activity(session, run)

        stage_result = await execute_platform_run(
            session,
            run,
            agent_stage=stage,
        )
        # Session may have committed inside the stage; reload for handoff/finalize.
        refreshed = await session.get(Run, run_id)
        if refreshed is None:
            raise RuntimeError(f"run vanished after stage: {run_id}")
        if stage_result.next_agent is not None:
            await schedule_next_agent_stage(
                session,
                refreshed,
                stage_result.next_agent,
                request_id=request_id,
            )
        elif stage_result.finalize_pending:
            await finalize_pending_completion(session, refreshed)
    except Exception as exc:
        await session.rollback()
        await _persist_run_failure(run_id, exc)
        raise
