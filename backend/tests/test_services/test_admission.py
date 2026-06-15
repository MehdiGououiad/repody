"""Admission control and queue position tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from audit_workbench.db.base import Base
from audit_workbench.db.models import Run, RunStatus, Workflow, WorkflowStatus
from audit_workbench.services.admission import (
    QueueCapacityExceeded,
    apply_queue_meta,
    check_admission,
    queue_position,
)
from audit_workbench.services.run_service import create_run
from audit_workbench.settings import clear_settings_cache


@pytest.fixture
async def admission_session(monkeypatch):
    monkeypatch.setenv("AUDIT_RUN_JOBS_INLINE", "false")
    clear_settings_cache()
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        wf = Workflow(id="wf-adm", name="Admission", status=WorkflowStatus.active.value)
        session.add(wf)
        await session.commit()
        yield session, wf.id

    await engine.dispose()
    clear_settings_cache()


def test_apply_queue_meta_sets_label_and_position():
    progress = apply_queue_meta(
        {
            "currentIndex": 0,
            "steps": [{"id": "queue", "label": "Queued", "status": "pending"}],
            "label": "x",
        },
        position=3,
        depth=10,
    )
    assert progress["queuePosition"] == 3
    assert progress["queueDepth"] == 10
    assert "3 of 10" in progress["label"]
    assert progress["steps"][0]["detail"] == "2 runs ahead of you in the queue."


@pytest.mark.asyncio
async def test_check_admission_rejects_when_queued_full(
    admission_session, monkeypatch: pytest.MonkeyPatch
):
    session, workflow_id = admission_session
    monkeypatch.setenv("AUDIT_ADMISSION_CONTROL_ENABLED", "true")
    monkeypatch.setenv("AUDIT_ADMISSION_MAX_QUEUED", "1")
    monkeypatch.setenv("AUDIT_ADMISSION_MAX_INFLIGHT", "100")
    clear_settings_cache()

    session.add(
        Run(
            id="AUD-QUEUED-1",
            workflow_id=workflow_id,
            source="test",
            status=RunStatus.queued.value,
        )
    )
    await session.flush()

    with pytest.raises(QueueCapacityExceeded) as exc:
        await check_admission(session, workflow_id=workflow_id, file_bindings=None)
    assert exc.value.scope == "queued"


@pytest.mark.asyncio
async def test_queue_position_for_waiting_run(admission_session):
    session, workflow_id = admission_session
    for run_id in ("AUD-Q-1", "AUD-Q-2", "AUD-Q-3"):
        session.add(
            Run(
                id=run_id,
                workflow_id=workflow_id,
                source="test",
                status=RunStatus.queued.value,
            )
        )
    await session.flush()

    position, depth = await queue_position(session, "AUD-Q-2")
    assert depth == 3
    assert position == 2


@pytest.mark.asyncio
async def test_create_run_progress_includes_queue_fields(admission_session):
    session, workflow_id = admission_session
    run = await create_run(session, workflow_id, source="test")
    await session.refresh(run)
    assert run.progress is not None
    assert run.progress.get("queuePosition") == 1
    assert run.progress.get("queueDepth") == 1


@pytest.mark.asyncio
async def test_count_ocr_inflight_uses_worker_pool_column(admission_session):
    from audit_workbench.db.models import RunDocument
    from audit_workbench.services.admission import count_ocr_inflight

    session, workflow_id = admission_session
    session.add(
        Run(
            id="AUD-OCR-1",
            workflow_id=workflow_id,
            source="test",
            status=RunStatus.running.value,
            worker_pool="ocr",
        )
    )
    session.add(
        Run(
            id="AUD-FAST-1",
            workflow_id=workflow_id,
            source="test",
            status=RunStatus.running.value,
            worker_pool="fast",
        )
    )
    session.add(
        RunDocument(
            id="rdoc-1",
            run_id="AUD-FAST-1",
            storage_key="runs/x/file.pdf",
            mime_type="application/pdf",
        )
    )
    await session.flush()
    assert await count_ocr_inflight(session) == 1
