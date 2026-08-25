"""Unit tests for deferred pendingCompletion finalization."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from repody.app.run.commands import finalize_pending_completion
from repody.app.run.lifecycle import RunCompletionOutcome
from repody.runtime.agent_metadata import (
    PendingCompletion,
    clear_pending_completion,
    pending_completion_from_run,
    store_pending_completion,
)
from repody.runtime.contracts.result import Result


def test_pending_completion_round_trip():
    run = SimpleNamespace(run_metadata=None)
    store_pending_completion(
        run,  # type: ignore[arg-type]
        PendingCompletion(
            overall_status="passed",
            summary_total=2,
            summary_passed=2,
            summary_failed=0,
            fields_extracted=3,
            run_metadata={"durationMs": 10},
            progress={"steps": []},
        ),
    )
    pending = pending_completion_from_run(run)  # type: ignore[arg-type]
    assert pending is not None
    assert pending.overall_status == "passed"
    assert pending.fields_extracted == 3
    clear_pending_completion(run)  # type: ignore[arg-type]
    assert pending_completion_from_run(run) is None  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_finalize_pending_completion_maps_to_complete_run(
    monkeypatch: pytest.MonkeyPatch,
):
    run = SimpleNamespace(
        id="run-1",
        run_metadata={"agentOutcomes": {"idp": {"status": "passed"}}},
    )
    store_pending_completion(
        run,  # type: ignore[arg-type]
        PendingCompletion(
            overall_status="passed",
            summary_total=1,
            summary_passed=1,
            summary_failed=0,
            fields_extracted=1,
            run_metadata={"durationMs": 5},
            progress=None,
        ),
    )
    session = AsyncMock()
    session.flush = AsyncMock()

    captured: dict = {}

    async def _fake_complete(request, **_kwargs):
        captured["outcome"] = request.outcome
        return Result.ok(None)

    monkeypatch.setattr(
        "repody.app.run.commands.complete_run",
        _fake_complete,
    )
    monkeypatch.setattr(
        "repody.app.run.commands.session_run_ports",
        lambda _s: (AsyncMock(), AsyncMock(), AsyncMock()),
    )
    monkeypatch.setattr(
        "repody.app.run.commands.publish_run_domain_events",
        AsyncMock(),
    )

    await finalize_pending_completion(session, run)  # type: ignore[arg-type]
    outcome = captured["outcome"]
    assert isinstance(outcome, RunCompletionOutcome)
    assert outcome.overall_status == "passed"
    assert outcome.run_metadata.get("durationMs") == 5
    assert outcome.run_metadata.get("agentOutcomes", {}).get("idp", {}).get("status") == "passed"
    assert pending_completion_from_run(run) is None  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_finalize_pending_completion_requires_payload():
    run = SimpleNamespace(id="run-missing", run_metadata=None)
    session = AsyncMock()
    with pytest.raises(RuntimeError, match="missing pendingCompletion"):
        await finalize_pending_completion(session, run)  # type: ignore[arg-type]
