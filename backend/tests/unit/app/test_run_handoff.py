"""Unit: handoff rejects reserved peer agents (recipe is IDP-only)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from repody.runtime.contracts.agent import AgentId
from repody.app.run.handoff import schedule_next_agent_stage


@pytest.mark.asyncio
async def test_schedule_next_agent_stage_rejects_unimplemented():
    session = AsyncMock()
    run = SimpleNamespace(id="run-1", worker_pool="extract", workflow_id="wf-1")
    with pytest.raises(RuntimeError, match="agent not implemented: fraud"):
        await schedule_next_agent_stage(session, run, AgentId.FRAUD)  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="agent not implemented: computer_use"):
        await schedule_next_agent_stage(
            session, run, AgentId.COMPUTER_USE  # type: ignore[arg-type]
        )
    session.get.assert_not_called()
