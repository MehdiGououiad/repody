from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from audit_workbench.services.run.application.use_cases import (
    CompleteRun,
    CompleteRunRequest,
    FailRun,
    FailRunRequest,
)
from audit_workbench.services.run.domain.entity import DomainRunStatus, RunEntity
from audit_workbench.services.run.domain.events import RunCompleted, RunDomainEvent, RunFailed
from audit_workbench.services.run.domain.lifecycle import RunCompletionOutcome


class FakeRunLifecycleStore:
    def __init__(self, entity: RunEntity | None) -> None:
        self.entity = entity
        self.saved: RunEntity | None = None
        self.commits = 0

    async def load(self, run_id: str) -> RunEntity | None:
        if self.entity is None or self.entity.id != run_id:
            return None
        return self.entity

    async def save(self, entity: RunEntity) -> None:
        self.saved = entity

    async def commit(self) -> None:
        self.commits += 1


class FakeRunEventPublisher:
    def __init__(self) -> None:
        self.published: list[RunDomainEvent] = []

    async def publish(self, events: Sequence[RunDomainEvent]) -> None:
        self.published.extend(events)


@pytest.mark.asyncio
async def test_fail_run_uses_ports_without_infrastructure() -> None:
    entity = RunEntity(
        id="run-1",
        workflow_id="wf-1",
        source="test",
        status=DomainRunStatus.running,
    )
    store = FakeRunLifecycleStore(entity)
    publisher = FakeRunEventPublisher()
    now = datetime.now(UTC)

    changed = await FailRun(publisher).execute(
        FailRunRequest(run_id="run-1", error="boom"),
        store=store,
        now=now,
    )

    assert changed is True
    assert store.saved is entity
    assert entity.status == DomainRunStatus.failed
    assert entity.error == "boom"
    assert entity.finished_at == now
    assert store.commits == 1
    assert len(publisher.published) == 1
    assert isinstance(publisher.published[0], RunFailed)


@pytest.mark.asyncio
async def test_fail_run_skips_when_expected_status_does_not_match() -> None:
    entity = RunEntity(
        id="run-1",
        workflow_id="wf-1",
        source="test",
        status=DomainRunStatus.queued,
    )
    store = FakeRunLifecycleStore(entity)
    publisher = FakeRunEventPublisher()

    changed = await FailRun(publisher).execute(
        FailRunRequest(
            run_id="run-1",
            error="boom",
            expected_status=DomainRunStatus.running,
        ),
        store=store,
    )

    assert changed is False
    assert store.saved is None
    assert entity.status == DomainRunStatus.queued
    assert store.commits == 0
    assert publisher.published == []


@pytest.mark.asyncio
async def test_complete_run_uses_lifecycle_store_port() -> None:
    entity = RunEntity(
        id="run-1",
        workflow_id="wf-1",
        source="test",
        status=DomainRunStatus.running,
    )
    store = FakeRunLifecycleStore(entity)
    publisher = FakeRunEventPublisher()
    now = datetime.now(UTC)

    await CompleteRun(publisher).execute(
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
        store=store,
        now=now,
    )

    assert store.saved is entity
    assert entity.status == DomainRunStatus.done
    assert entity.overall_status == "passed"
    assert entity.finished_at == now
    assert entity.progress == {"status": "done"}
    assert store.commits == 1
    assert len(publisher.published) == 1
    assert isinstance(publisher.published[0], RunCompleted)
