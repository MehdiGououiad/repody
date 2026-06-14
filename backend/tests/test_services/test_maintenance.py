from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from audit_workbench.db.base import Base
from audit_workbench.db.models import Run, RunStatus, Workflow, WorkflowStatus
from audit_workbench.services.maintenance import reap_stale_runs
from audit_workbench.services.run_dispatch import mark_run_dispatch_failed


@pytest.fixture
async def maintenance_session(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    import audit_workbench.db.base as db_base

    monkeypatch.setattr(db_base, "async_session_factory", session_factory)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        wf = Workflow(id="wf-maint", name="Maint", status=WorkflowStatus.active.value)
        session.add(wf)
        await session.commit()
        yield session

    await engine.dispose()


@pytest.fixture
def mock_progress(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr(
        "audit_workbench.services.run_events.publish_run_progress",
        mock,
    )
    return mock


@pytest.mark.asyncio
async def test_reap_stale_runs_marks_old_running_failed(
    maintenance_session, mock_progress, monkeypatch
):
    session = maintenance_session
    monkeypatch.setattr(
        "audit_workbench.services.maintenance.get_settings",
        lambda: type(
            "S",
            (),
            {"stale_run_timeout_minutes": 20, "queued_stale_timeout_minutes": 5},
        )(),
    )
    stale = Run(
        id="run-stale",
        workflow_id="wf-maint",
        status=RunStatus.running.value,
        started_at=datetime(2020, 1, 1, tzinfo=UTC),
    )
    fresh = Run(
        id="run-fresh",
        workflow_id="wf-maint",
        status=RunStatus.running.value,
        started_at=datetime.now(UTC) - timedelta(minutes=2),
    )
    session.add_all([stale, fresh])
    await session.commit()

    count = await reap_stale_runs(session=session)
    assert count == 1

    await session.refresh(stale)
    await session.refresh(fresh)
    assert stale.status == RunStatus.failed.value
    assert stale.error is not None
    assert stale.progress is not None
    assert stale.progress.get("failed") is True
    assert fresh.status == RunStatus.running.value
    mock_progress.assert_called_once()


@pytest.mark.asyncio
async def test_reap_stale_queued_runs(maintenance_session, mock_progress, monkeypatch):
    session = maintenance_session
    monkeypatch.setattr(
        "audit_workbench.services.maintenance.get_settings",
        lambda: type(
            "S",
            (),
            {"stale_run_timeout_minutes": 20, "queued_stale_timeout_minutes": 5},
        )(),
    )
    stale = Run(
        id="run-queued-stale",
        workflow_id="wf-maint",
        status=RunStatus.queued.value,
        created_at=datetime(2020, 1, 1, tzinfo=UTC),
    )
    fresh = Run(
        id="run-queued-fresh",
        workflow_id="wf-maint",
        status=RunStatus.queued.value,
        created_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    session.add_all([stale, fresh])
    await session.commit()

    count = await reap_stale_runs(session=session)
    assert count == 1

    await session.refresh(stale)
    await session.refresh(fresh)
    assert stale.status == RunStatus.failed.value
    assert "queued" in (stale.error or "").lower()
    assert fresh.status == RunStatus.queued.value


@pytest.mark.asyncio
async def test_reap_stale_queued_runs_skipped_when_worker_busy(
    maintenance_session, mock_progress, monkeypatch
):
    session = maintenance_session
    monkeypatch.setattr(
        "audit_workbench.services.maintenance.get_settings",
        lambda: type(
            "S",
            (),
            {"stale_run_timeout_minutes": 20, "queued_stale_timeout_minutes": 5},
        )(),
    )
    stale_queued = Run(
        id="run-queued-waiting",
        workflow_id="wf-maint",
        status=RunStatus.queued.value,
        created_at=datetime(2020, 1, 1, tzinfo=UTC),
    )
    active = Run(
        id="run-active-ocr",
        workflow_id="wf-maint",
        status=RunStatus.running.value,
        started_at=datetime.now(UTC) - timedelta(minutes=2),
    )
    session.add_all([stale_queued, active])
    await session.commit()

    count = await reap_stale_runs(session=session)
    assert count == 0

    await session.refresh(stale_queued)
    assert stale_queued.status == RunStatus.queued.value


@pytest.mark.asyncio
async def test_mark_run_dispatch_failed(maintenance_session, mock_progress):
    session = maintenance_session
    run = Run(
        id="run-dispatch-fail",
        workflow_id="wf-maint",
        status=RunStatus.queued.value,
    )
    session.add(run)
    await session.commit()

    await mark_run_dispatch_failed("run-dispatch-fail", RuntimeError("hatchet down"))

    await session.refresh(run)
    assert run.status == RunStatus.failed.value
    assert "dispatch failed" in (run.error or "").lower()
    assert run.finished_at is not None
    mock_progress.assert_called_once()
