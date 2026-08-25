from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from repody.app.run.commands import (
    CompleteRunRequest,
    FailRunRequest,
    complete_run,
    fail_run,
)
from repody.app.run.lifecycle import (
    RunCompleted,
    RunCompletionOutcome,
    RunDomainEvent,
    RunEntity,
    RunFailed,
    RunStatus,
)


def _store(entity: RunEntity | None):
    saved: dict[str, RunEntity | None] = {"entity": entity, "saved": None}
    commits = {"n": 0}

    async def load(run_id: str) -> RunEntity | None:
        current = saved["entity"]
        if current is None or current.id != run_id:
            return None
        return current

    async def save(item: RunEntity) -> None:
        saved["saved"] = item

    async def commit() -> None:
        commits["n"] += 1

    return load, save, commit, saved, commits


def _publisher():
    published: list[RunDomainEvent] = []

    async def publish(events: Sequence[RunDomainEvent]) -> None:
        published.extend(events)

    return publish, published


@pytest.mark.asyncio
async def test_fail_run_uses_ports_without_infrastructure() -> None:
    entity = RunEntity(
        id="run-1",
        workflow_id="wf-1",
        source="test",
        status=RunStatus.running,
    )
    load, save, commit, saved, commits = _store(entity)
    publish, published = _publisher()
    now = datetime.now(UTC)

    changed = await fail_run(
        FailRunRequest(run_id="run-1", error="boom"),
        load=load,
        save=save,
        commit=commit,
        publish=publish,
        now=now,
    )

    assert changed is True
    assert saved["saved"] is entity
    assert entity.status == RunStatus.failed
    assert entity.error == "boom"
    assert entity.finished_at == now
    assert commits["n"] == 1
    assert len(published) == 1
    assert isinstance(published[0], RunFailed)


@pytest.mark.asyncio
async def test_fail_run_skips_when_expected_status_does_not_match() -> None:
    entity = RunEntity(
        id="run-1",
        workflow_id="wf-1",
        source="test",
        status=RunStatus.queued,
    )
    load, save, commit, saved, commits = _store(entity)
    publish, published = _publisher()

    changed = await fail_run(
        FailRunRequest(
            run_id="run-1",
            error="boom",
            expected_status=RunStatus.running,
        ),
        load=load,
        save=save,
        commit=commit,
        publish=publish,
    )

    assert changed is False
    assert saved["saved"] is None
    assert entity.status == RunStatus.queued
    assert commits["n"] == 0
    assert published == []


@pytest.mark.asyncio
async def test_complete_run_uses_lifecycle_store_port() -> None:
    entity = RunEntity(
        id="run-1",
        workflow_id="wf-1",
        source="test",
        status=RunStatus.running,
    )
    load, save, commit, saved, commits = _store(entity)
    publish, published = _publisher()
    now = datetime.now(UTC)

    result = await complete_run(
        CompleteRunRequest(
            run_id="run-1",
            outcome=RunCompletionOutcome(
                overall_status="passed",
                summary_total=1,
                summary_passed=1,
                summary_failed=0,
                fields_extracted=3,
                run_metadata={"durationMs": 100},
                progress={"status": "done"},
            ),
        ),
        load=load,
        save=save,
        commit=commit,
        publish=publish,
        now=now,
    )

    assert result.is_ok
    assert saved["saved"] is entity
    assert entity.status == RunStatus.done
    assert entity.overall_status == "passed"
    assert entity.finished_at == now
    assert entity.progress == {"status": "done"}
    assert commits["n"] == 1
    assert len(published) == 1
    assert isinstance(published[0], RunCompleted)
