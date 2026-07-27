"""Finalize deferred run completion after the last non-IDP agent stage."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.models import Run
from audit_workbench.platform.agent_metadata import (
    clear_pending_completion,
    pending_completion_from_run,
)
from audit_workbench.services.run.commands import CompleteRunRequest, complete_run
from audit_workbench.services.run.events import publish_run_domain_events
from audit_workbench.services.run.lifecycle import RunCompletionOutcome
from audit_workbench.services.run.persistence import bind_commit, bind_load, bind_save


async def finalize_pending_completion(session: AsyncSession, run: Run) -> None:
    """Complete a run from ``run_metadata.pendingCompletion`` (final non-IDP stage)."""
    pending = pending_completion_from_run(run)
    if pending is None:
        raise RuntimeError(f"missing pendingCompletion for run {run.id}")
    clear_pending_completion(run)
    await session.flush()
    completed = await complete_run(
        CompleteRunRequest(
            run_id=run.id,
            outcome=RunCompletionOutcome(
                overall_status=pending.overall_status,
                summary_total=pending.summary_total,
                summary_passed=pending.summary_passed,
                summary_failed=pending.summary_failed,
                fields_extracted=pending.fields_extracted,
                run_metadata=pending.run_metadata,
                progress=pending.progress,
            ),
        ),
        load=bind_load(session),
        save=bind_save(session),
        commit=bind_commit(session),
        publish=publish_run_domain_events,
        now=datetime.now(UTC),
    )
    if not completed.is_ok:
        err = completed.error
        raise RuntimeError(err.message if err else "complete_run failed")
