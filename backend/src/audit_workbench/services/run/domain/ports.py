from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from audit_workbench.services.run.domain.entity import RunEntity
from audit_workbench.services.run.domain.events import RunDomainEvent


class RunLifecycleStorePort(Protocol):
    """Output port for one transactional Run lifecycle change."""

    async def load(self, run_id: str) -> RunEntity | None: ...

    async def save(self, entity: RunEntity) -> None: ...

    async def commit(self) -> None: ...


class RunClaimStorePort(Protocol):
    """Output port for atomically claiming queued work."""

    async def try_claim_queued(self, run_id: str, now: datetime) -> RunEntity | None: ...


class RunEventPublisherPort(Protocol):
    """Output port for publishing Run domain events."""

    async def publish(self, events: Sequence[RunDomainEvent]) -> None: ...
