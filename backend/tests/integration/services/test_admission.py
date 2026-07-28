"""Queue depth counters, admission caps, and queue position tests."""

from __future__ import annotations

import pytest

from audit_workbench.db.models import Run, RunStatus, Workflow, WorkflowStatus
from audit_workbench.platform.contracts.result import ErrorCode
from audit_workbench.services.admission import (
    check_admission,
    count_extract_inflight,
    count_queued,
    count_running,
)
from audit_workbench.services.queue import apply_queue_meta, queue_position
from audit_workbench.services.run.intake import create_run
from audit_workbench.settings import clear_settings_cache


@pytest.fixture
async def admission_session(postgres_session):
    wf = Workflow(id="wf-adm", name="Admission", status=WorkflowStatus.active.value)
    postgres_session.add(wf)
    await postgres_session.flush()
    await postgres_session.commit()
    yield postgres_session, wf.id


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
    created = await create_run(session, workflow_id, source="test")
    assert created.is_ok
    run = created.unwrap()
    await session.refresh(run)
    assert run.progress is not None
    assert run.progress.get("queuePosition") == 1
    assert run.progress.get("queueDepth") == 1


@pytest.mark.asyncio
async def test_count_running_excludes_queued(admission_session):
    session, workflow_id = admission_session
    session.add(
        Run(
            id="AUD-R-1",
            workflow_id=workflow_id,
            source="test",
            status=RunStatus.running.value,
        )
    )
    session.add(
        Run(
            id="AUD-Q-9",
            workflow_id=workflow_id,
            source="test",
            status=RunStatus.queued.value,
        )
    )
    await session.flush()
    assert await count_running(session) == 1
    assert await count_queued(session) == 1


@pytest.mark.asyncio
async def test_count_extract_inflight_uses_worker_pool_column(admission_session):
    from audit_workbench.db.models import RunDocument

    session, workflow_id = admission_session
    session.add(
        Run(
            id="AUD-OCR-1",
            workflow_id=workflow_id,
            source="test",
            status=RunStatus.running.value,
            worker_pool="extract",
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
    assert await count_extract_inflight(session) == 1


@pytest.mark.asyncio
async def test_check_admission_rejects_when_queued_at_cap(admission_session, monkeypatch):
    session, workflow_id = admission_session
    monkeypatch.setenv("AUDIT_ADMISSION_MAX_QUEUED", "2")
    monkeypatch.setenv("AUDIT_ADMISSION_MAX_INFLIGHT", "0")
    monkeypatch.setenv("AUDIT_ADMISSION_MAX_EXTRACT_INFLIGHT", "0")
    clear_settings_cache()
    for i in range(2):
        session.add(
            Run(
                id=f"AUD-CAP-{i}",
                workflow_id=workflow_id,
                source="test",
                status=RunStatus.queued.value,
            )
        )
    await session.flush()
    result = await check_admission(session, predicted_pool="fast")
    assert not result.is_ok
    assert result.error is not None
    assert result.error.code is ErrorCode.CAPACITY
    assert result.error.retry_after_seconds is not None
