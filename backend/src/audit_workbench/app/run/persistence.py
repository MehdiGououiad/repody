"""SQLAlchemy run persistence as plain functions."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.infra.db.models import Run
from audit_workbench.infra.db.models.enums import RunStatus as OrmRunStatus
from audit_workbench.app.run.lifecycle import RunStatus, RunEntity
from audit_workbench.app.run.lifecycle import start_field_updates


def _to_domain_status(value: str) -> RunStatus:
    return RunStatus(value)


def _to_orm_status(status: RunStatus) -> str:
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
        last_activity_at=run.last_activity_at,
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
    run.last_activity_at = entity.last_activity_at
    run.finished_at = entity.finished_at
    run.run_metadata = entity.run_metadata
    run.progress = entity.progress


def _start_claim_orm_values(now: datetime) -> dict[str, object]:
    updates = start_field_updates(now)
    values = asdict(updates)
    values["status"] = _to_orm_status(updates.status)
    return values


async def load_run_entity(session: AsyncSession, run_id: str) -> RunEntity | None:
    run = await session.get(Run, run_id)
    if run is None:
        return None
    return entity_from_orm(run)


async def save_run_entity(session: AsyncSession, entity: RunEntity) -> None:
    run = await session.get(Run, entity.id)
    if run is None:
        raise ValueError(f"Run not found: {entity.id}")
    apply_entity_to_orm(entity, run)


async def try_claim_queued_run(
    session: AsyncSession,
    run_id: str,
    now: datetime,
) -> RunEntity | None:
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
        status=RunStatus.running,
        started_at=now,
        last_activity_at=now,
    )


async def commit_session(session: AsyncSession) -> None:
    await session.commit()


def bind_load(session: AsyncSession):
    async def load(run_id: str) -> RunEntity | None:
        return await load_run_entity(session, run_id)

    return load


def bind_save(session: AsyncSession):
    async def save(entity: RunEntity) -> None:
        await save_run_entity(session, entity)

    return save


def bind_commit(session: AsyncSession):
    async def commit() -> None:
        await commit_session(session)

    return commit


def bind_try_claim(session: AsyncSession):
    async def try_claim(run_id: str, now: datetime) -> RunEntity | None:
        return await try_claim_queued_run(session, run_id, now)

    return try_claim
