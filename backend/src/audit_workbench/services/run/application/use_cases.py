from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from audit_workbench.services.run.domain.entity import DomainRunStatus, RunEntity
from audit_workbench.services.run.domain.events import RunDomainEvent
from audit_workbench.services.run.domain.lifecycle import RunCompletionOutcome, RunLifecycle
from audit_workbench.services.run.domain.ports import (
    RunClaimStorePort,
    RunEventPublisherPort,
    RunLifecycleStorePort,
)


@dataclass(frozen=True)
class FailRunRequest:
    run_id: str
    error: str
    expected_status: DomainRunStatus | None = None


class FailRun:
    """Use case — mark a run failed and publish domain events."""

    def __init__(
        self,
        publisher: RunEventPublisherPort,
    ) -> None:
        self._publisher = publisher

    async def execute(
        self,
        request: FailRunRequest,
        *,
        store: RunLifecycleStorePort,
        now: datetime | None = None,
    ) -> bool:
        occurred_at = now or datetime.now(UTC)

        entity = await store.load(request.run_id)
        if entity is None:
            return False
        lifecycle = RunLifecycle(entity)
        if (
            lifecycle.fail(
                request.error,
                occurred_at,
                expected_status=request.expected_status,
            )
            is None
        ):
            return False
        await store.save(entity)
        events = lifecycle.collect_events()
        await store.commit()
        await self._publisher.publish(events)
        return True


@dataclass(frozen=True)
class ClaimRunRequest:
    run_id: str


@dataclass(frozen=True)
class ClaimRunResult:
    entity: RunEntity
    events: list[RunDomainEvent]


class ClaimRun:
    """Use case — atomically claim a queued run and produce RunStarted domain events."""

    async def execute(
        self,
        request: ClaimRunRequest,
        *,
        claim_store: RunClaimStorePort,
        now: datetime | None = None,
    ) -> ClaimRunResult | None:
        occurred_at = now or datetime.now(UTC)
        entity = await claim_store.try_claim_queued(request.run_id, occurred_at)
        if entity is None:
            return None
        lifecycle = RunLifecycle(entity)
        lifecycle.record_claimed(occurred_at)
        return ClaimRunResult(entity=entity, events=lifecycle.collect_events())


@dataclass(frozen=True)
class CompleteRunRequest:
    run_id: str
    outcome: RunCompletionOutcome


class CompleteRun:
    """Use case — finalize a successful run after validation."""

    def __init__(
        self,
        publisher: RunEventPublisherPort,
    ) -> None:
        self._publisher = publisher

    async def execute(
        self,
        request: CompleteRunRequest,
        *,
        store: RunLifecycleStorePort,
        now: datetime | None = None,
    ) -> None:
        occurred_at = now or datetime.now(UTC)
        entity = await store.load(request.run_id)
        if entity is None:
            raise ValueError(f"Run not found: {request.run_id}")
        lifecycle = RunLifecycle(entity)
        lifecycle.complete(request.outcome, occurred_at)
        await store.save(entity)
        events = lifecycle.collect_events()
        await store.commit()
        await self._publisher.publish(events)
