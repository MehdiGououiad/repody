from __future__ import annotations

from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.services.run.adapters.event_publisher import RunDomainEventPublisher
from audit_workbench.services.run.adapters.persistence import (
    SqlAlchemyRunClaimStore,
    SqlAlchemyRunLifecycleStore,
)
from audit_workbench.services.run.application.use_cases import ClaimRun, CompleteRun, FailRun


@lru_cache(maxsize=1)
def _publisher() -> RunDomainEventPublisher:
    return RunDomainEventPublisher()


@lru_cache(maxsize=1)
def get_run_publisher() -> RunDomainEventPublisher:
    return _publisher()


@lru_cache(maxsize=1)
def get_claim_run() -> ClaimRun:
    return ClaimRun()


@lru_cache(maxsize=1)
def get_fail_run() -> FailRun:
    return FailRun(_publisher())


@lru_cache(maxsize=1)
def get_complete_run() -> CompleteRun:
    return CompleteRun(_publisher())


def run_lifecycle_store(session: AsyncSession) -> SqlAlchemyRunLifecycleStore:
    return SqlAlchemyRunLifecycleStore(session)


def run_claim_store(session: AsyncSession) -> SqlAlchemyRunClaimStore:
    return SqlAlchemyRunClaimStore(session)
