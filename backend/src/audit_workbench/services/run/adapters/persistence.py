from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.models import Run
from audit_workbench.db.models.enums import RunStatus as OrmRunStatus
from audit_workbench.services.run.domain.entity import DomainRunStatus, RunEntity
from audit_workbench.services.run.domain.lifecycle import RunLifecycle


def _to_domain_status(value: str) -> DomainRunStatus:
    return DomainRunStatus(value)


def _to_orm_status(status: DomainRunStatus) -> str:
    return status.value


def entity_from_orm(run: Run) -> RunEntity:
    return RunEntity(
        id=run.id,
        workflow_id=run.workflow_id,
        source=run.source,
        status=_to_domain_status(run.status),
        worker_pool=run.worker_pool,
        overall_status=run.overall_status,
        error=run.error,
        summary_total=run.summary_total,
        summary_passed=run.summary_passed,
        summary_failed=run.summary_failed,
        fields_extracted=run.fields_extracted,
        started_at=run.started_at,
        finished_at=run.finished_at,
        run_metadata=run.run_metadata,
        progress=run.progress,
    )


def apply_entity_to_orm(entity: RunEntity, run: Run) -> None:
    run.status = _to_orm_status(entity.status)
    run.overall_status = entity.overall_status
    run.error = entity.error
    run.summary_total = entity.summary_total
    run.summary_passed = entity.summary_passed
    run.summary_failed = entity.summary_failed
    run.fields_extracted = entity.fields_extracted
    run.started_at = entity.started_at
    run.finished_at = entity.finished_at
    run.run_metadata = entity.run_metadata
    run.progress = entity.progress


def _start_claim_orm_values(now: datetime) -> dict[str, object]:
    updates = RunLifecycle.start_field_updates(now)
    values = asdict(updates)
    values["status"] = _to_orm_status(updates.status)
    return values


class SqlAlchemyRunRepository:
    """Gateway — maps between RunEntity and SQLAlchemy persistence."""

    async def load(self, session: object, run_id: str) -> RunEntity | None:
        if not isinstance(session, AsyncSession):
            raise TypeError("SqlAlchemyRunRepository requires AsyncSession")
        run = await session.get(Run, run_id)
        if run is None:
            return None
        return entity_from_orm(run)

    async def save(self, session: object, entity: RunEntity) -> None:
        if not isinstance(session, AsyncSession):
            raise TypeError("SqlAlchemyRunRepository requires AsyncSession")
        run = await session.get(Run, entity.id)
        if run is None:
            raise ValueError(f"Run not found: {entity.id}")
        apply_entity_to_orm(entity, run)

    async def try_claim_queued(
        self,
        session: object,
        run_id: str,
        now: datetime,
    ) -> RunEntity | None:
        if not isinstance(session, AsyncSession):
            raise TypeError("SqlAlchemyRunRepository requires AsyncSession")
        claim = await session.execute(
            update(Run)
            .where(Run.id == run_id, Run.status == OrmRunStatus.queued.value)
            .values(**_start_claim_orm_values(now))
            .returning(Run.id, Run.workflow_id)
        )
        row = claim.one_or_none()
        if row is None:
            return None
        _, workflow_id = row
        return RunEntity(
            id=run_id,
            workflow_id=workflow_id,
            source="",
            status=DomainRunStatus.running,
            started_at=now,
        )


class SqlAlchemyRunLifecycleStore:
    """Adapter for one transactional Run lifecycle change."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = SqlAlchemyRunRepository()

    async def load(self, run_id: str) -> RunEntity | None:
        return await self._repository.load(self._session, run_id)

    async def save(self, entity: RunEntity) -> None:
        await self._repository.save(self._session, entity)

    async def commit(self) -> None:
        await self._session.commit()


class SqlAlchemyRunClaimStore:
    """Adapter for atomically claiming queued worker work."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = SqlAlchemyRunRepository()

    async def try_claim_queued(self, run_id: str, now: datetime) -> RunEntity | None:
        return await self._repository.try_claim_queued(self._session, run_id, now)
