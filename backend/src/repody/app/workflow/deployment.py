"""Workflow deploy and API key lifecycle."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from repody.infra.db.models import WorkflowStatus
from repody.schemas.workflow import WorkflowSchema
from repody.app.api_keys import api_key_hint, hash_api_key
from repody.app.mappers import workflow_to_schema
from repody.app.workflow.repository import load_workflow
from repody.app.workflow.stats import workflow_api_stats, workflow_stats


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
