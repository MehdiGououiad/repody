"""Workflow deploy and API key lifecycle."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.models import WorkflowStatus
from audit_workbench.schemas.workflow import WorkflowSchema
from audit_workbench.services.api_keys import api_key_hint, hash_api_key
from audit_workbench.services.mappers import load_workflow, workflow_stats, workflow_to_schema
from audit_workbench.services.workflow_stats import workflow_api_stats


async def deploy_workflow(
    session: AsyncSession,
    workflow_id: str,
    api_key: str | None = None,
) -> WorkflowSchema | None:
    wf = await load_workflow(session, workflow_id)
    if not wf:
        return None
    wf.deployed_at = datetime.now(UTC)
    wf.status = WorkflowStatus.active.value
    raw_key = api_key or f"wbk_live_{secrets.token_hex(16)}"
    wf.api_key = hash_api_key(raw_key)
    wf.api_key_hint = api_key_hint(raw_key)
    await session.flush()
    total, rate, last = await workflow_stats(session, workflow_id)
    api_stats = await workflow_api_stats(session, workflow_id)
    return workflow_to_schema(
        wf,
        total_runs=total,
        success_rate=rate,
        last_run=last,
        api_stats=api_stats,
        reveal_api_key=raw_key,
    )
