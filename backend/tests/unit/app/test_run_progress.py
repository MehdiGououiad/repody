from __future__ import annotations

import pytest

from audit_workbench.app.run.progress import (
    _last_progress_commit,
    set_run_progress,
)
from audit_workbench.app.run.progress import _step, build_run_progress_plan
from audit_workbench.app.run.snapshot import SnapshotDocument, SnapshotSchemaField


@pytest.fixture(autouse=True)
def _clear_progress_throttle():
    _last_progress_commit.clear()
    yield
    _last_progress_commit.clear()


class _ThrottleSettings:
    progress_commit_interval_ms = 60_000


def test_progress_plan_supports_snapshot_documents():
    document = SnapshotDocument(
        id="doc-1",
        document_type="Invoice",
        position=0,
        extraction_mode="document_model",
        validation_mode="logic_only",
        document_model_id="repody:vlm",
        schema_fields=[
            SnapshotSchemaField(
                id="field-1",
                name="total",
                description="Invoice total",
                position=0,
            )
        ],
    )

    steps = build_run_progress_plan(
        workflow_docs=[document],
        rules=[],
        docs_with_files={"doc-1"},
    )

    assert steps[1]["id"] == "extract-doc-1"
    assert steps[1]["readPath"] == "document_model"
    assert steps[1]["validationMode"] == "logic_only"
    assert "Read:" in steps[1]["detail"]
    assert "Validation:" not in steps[1]["detail"]


def test_step_index_for_resolves_by_id():
    from audit_workbench.app.run.progress import step_index_for

    steps = [
        {"id": "queue"},
        {"id": "extract-doc-1"},
        {"id": "rule-r1"},
        {"id": "finalize"},
    ]
    assert step_index_for(steps, "extract-doc-1") == 1
    assert step_index_for(steps, "rule-r1") == 2
    assert step_index_for(steps, "missing") is None


def test_progress_snapshot_marks_only_current_active():
    from audit_workbench.app.run.progress import progress_snapshot

    steps = [
        {"id": "queue", "label": "Q"},
        {"id": "extract-doc-1", "label": "E"},
        {"id": "rule-r1", "label": "V"},
        {"id": "finalize", "label": "F"},
    ]
    snap = progress_snapshot(steps, 1, "Extracting…")
    assert [s["status"] for s in snap["steps"]] == ["done", "active", "pending", "pending"]
    # Regression: advancing past extract must not happen while extraction runs.
    snap_wrong = progress_snapshot(steps, 2, "Would look like validation")
    assert snap_wrong["steps"][1]["status"] == "done"
    assert snap_wrong["steps"][2]["status"] == "active"


def test_progress_plan_includes_markdown_only_documents():
    document = SnapshotDocument(
        id="doc-md",
        document_type="Document",
        position=0,
        extraction_mode="document_model",
        validation_mode="logic_only",
        document_model_id="repody:vlm",
        markdown_extraction=True,
        schema_fields=[],
    )

    steps = build_run_progress_plan(
        workflow_docs=[document],
        rules=[],
        docs_with_files={"doc-md"},
    )

    assert steps[1]["id"] == "extract-doc-md"


@pytest.mark.asyncio
async def test_progress_sse_published_even_when_db_throttled(monkeypatch):
    published: list[dict] = []
    db_opened = False

    async def _publish(run_id: str, progress: dict) -> None:
        published.append({"run_id": run_id, "progress": progress})

    class _Run:
        progress = None

    class _Session:
        async def get(self, _model, run_id: str):
            return _Run()

        async def commit(self):
            nonlocal db_opened
            db_opened = True

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    def _session_factory():
        return _Session()

    monkeypatch.setattr("audit_workbench.app.run.sse.publish_run_progress", _publish)
    monkeypatch.setattr("audit_workbench.infra.db.base.async_session_factory", _session_factory)
    monkeypatch.setattr(
        "audit_workbench.app.run.progress.get_settings",
        lambda: _ThrottleSettings(),
    )

    steps = [_step("queue", "Queued")]
    await set_run_progress(None, "run-1", steps, 0, "Primed", force=True)
    published.clear()
    db_opened = False

    await set_run_progress(None, "run-1", steps, 0, "Working…", force=False)

    assert len(published) == 1
    assert published[0]["progress"]["label"] == "Working…"
    assert db_opened is False


@pytest.mark.asyncio
async def test_progress_db_written_when_forced(monkeypatch):
    published: list[dict] = []
    db_writes = 0

    async def _publish(run_id: str, progress: dict) -> None:
        published.append(progress)

    class _Run:
        progress = None

    class _Session:
        async def get(self, _model, run_id: str):
            return _Run()

        async def commit(self):
            nonlocal db_writes
            db_writes += 1

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    def _session_factory():
        return _Session()

    monkeypatch.setattr("audit_workbench.app.run.sse.publish_run_progress", _publish)
    monkeypatch.setattr("audit_workbench.infra.db.base.async_session_factory", _session_factory)
    monkeypatch.setattr(
        "audit_workbench.app.run.progress.get_settings",
        lambda: _ThrottleSettings(),
    )

    steps = [_step("queue", "Queued")]
    await set_run_progress(None, "run-2", steps, 0, "Done", force=True)

    assert len(published) == 1
    assert db_writes == 1
