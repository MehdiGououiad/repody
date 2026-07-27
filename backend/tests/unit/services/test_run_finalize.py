"""Unit tests for deferred pendingCompletion finalization."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from audit_workbench.platform.agent_metadata import (
    PendingCompletion,
    clear_pending_completion,
    pending_completion_from_run,
    store_pending_completion,
)
from audit_workbench.platform.contracts.result import Result
from audit_workbench.services.run.finalize import finalize_pending_completion
from audit_workbench.services.run.lifecycle import RunCompletionOutcome


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
    run = SimpleNamespace(id="run-1", run_metadata=None)
    store_pending_completion(
        run,  # type: ignore[arg-type]
        PendingCompletion(
            overall_status="passed",
            summary_total=1,
            summary_passed=1,
            summary_failed=0,
            fields_extracted=1,
            run_metadata={},
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
        "audit_workbench.services.run.finalize.complete_run",
        _fake_complete,
    )
    monkeypatch.setattr(
        "audit_workbench.services.run.finalize.bind_load",
        lambda _s: AsyncMock(),
    )
    monkeypatch.setattr(
        "audit_workbench.services.run.finalize.bind_save",
        lambda _s: AsyncMock(),
    )
    monkeypatch.setattr(
        "audit_workbench.services.run.finalize.bind_commit",
        lambda _s: AsyncMock(),
    )
    monkeypatch.setattr(
        "audit_workbench.services.run.finalize.publish_run_domain_events",
        AsyncMock(),
    )

    await finalize_pending_completion(session, run)  # type: ignore[arg-type]
    outcome = captured["outcome"]
    assert isinstance(outcome, RunCompletionOutcome)
    assert outcome.overall_status == "passed"
    assert pending_completion_from_run(run) is None  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_finalize_pending_completion_requires_payload():
    run = SimpleNamespace(id="run-missing", run_metadata=None)
    session = AsyncMock()
    with pytest.raises(RuntimeError, match="missing pendingCompletion"):
        await finalize_pending_completion(session, run)  # type: ignore[arg-type]
