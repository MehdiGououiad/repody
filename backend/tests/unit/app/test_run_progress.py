from __future__ import annotations

import pytest

from repody.app.run.progress import (
    build_run_progress_plan,
    progress_snapshot,
    progress_step,
    set_run_progress,
    step_index_for,
)
from repody.app.run.snapshot import SnapshotDocument
from repody.extraction.types import SchemaFieldSpec


def test_progress_plan_supports_snapshot_documents():
    document = SnapshotDocument(
        id="doc-1",
        document_type="Invoice",
        position=0,
        schema_fields=[SchemaFieldSpec(name="total", description="Invoice total")],
    )

    steps = build_run_progress_plan(
        workflow_docs=[document],
        rules=[],
        docs_with_files={"doc-1"},
    )

    assert steps[1]["id"] == "extract-doc-1"
    assert steps[1]["mode"] == "document_model"


def test_step_index_for_resolves_by_id():
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
        markdown_extraction=True,
        schema_fields=[],
    )

    steps = build_run_progress_plan(
        workflow_docs=[document],
        rules=[],
        docs_with_files={"doc-md"},
    )

    assert steps[1]["id"] == "extract-doc-md"


class _Run:
    progress = None


class _Session:
    def __init__(self, writes: list[dict]):
        self.writes = writes
        self.run = _Run()

    async def get(self, _model, _run_id: str):
        return self.run

    async def commit(self):
        self.writes.append(self.run.progress)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


@pytest.mark.asyncio
@pytest.mark.parametrize("persist", [True, False])
async def test_progress_is_always_published_and_stored_only_when_asked(monkeypatch, persist):
    published: list[dict] = []
    writes: list[dict] = []

    async def _publish(_run_id: str, progress: dict) -> None:
        published.append(progress)

    monkeypatch.setattr("repody.app.run.progress.publish_run_progress", _publish)
    monkeypatch.setattr("repody.infra.db.base.async_session_factory", lambda: _Session(writes))

    steps = [progress_step("queue", "Queued")]
    await set_run_progress(None, "run-1", steps, 0, "Working…", persist=persist)

    assert [p["label"] for p in published] == ["Working…"]
    assert len(writes) == (1 if persist else 0)
