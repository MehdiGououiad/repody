import csv
import io
import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, update

from repody.app import runs
from repody.app.runs import purge_expired
from repody.infra import db
from repody.infra.models import Run
from repody.infra.storage import get_store
from repody.settings import get_settings
from tests.files import FILE
from tests.integration.helpers import condition, invoice_workflow, rule


async def run(api, model: dict, answer: dict | None = None, workflow_id: str = "wf-a") -> str:
    """Start a test run whose model answers ``answer``; its run id."""
    model["text"] = json.dumps(answer or {})
    started = await api.post(f"/v1/workflows/{workflow_id}/runs", files=FILE)
    assert started.status_code == 202, started.text
    return started.json()["runId"]


async def test_table_rules_read_columns_named_with_spaces(api, model_answer):
    workflow = {
        "name": "Statements",
        "documents": [
            {
                "id": "doc",
                "documentType": "Statement",
                "schema": [
                    {
                        "id": "t",
                        "name": "Lines",
                        "templateType": "object-array",
                        "children": [
                            {"id": "c1", "name": "Label"},
                            {"id": "c2", "name": "Unit Price", "templateType": "number"},
                        ],
                    }
                ],
            }
        ],
        "rules": [
            rule(
                "sum",
                {
                    "id": "c",
                    "left": {"kind": "aggregate", "fn": "sum_rows", "table": "Lines", "column": "Unit Price"},
                    "operator": "==",
                    "right": {"kind": "literal", "value": "15"},
                },
            )
        ],
    }  # fmt: skip
    saved = await api.put("/v1/workflows/wf-a", json=workflow)
    assert saved.status_code == 200, saved.text
    answer = {"Lines": [{"Label": "a", "Unit Price": 10}, {"Label": "b", "Unit Price": 5}]}
    run_id = await run(api, model_answer, answer)
    report = (await api.get(f"/v1/audits/{run_id}")).json()
    assert report["ruleResults"][0]["status"] == "passed", report["ruleResults"][0]["detail"]

    workflow["rules"][0]["conditions"][0]["left"]["column"] = "Label"
    rejected = await api.put("/v1/workflows/wf-a", json=workflow)
    assert rejected.status_code == 422
    assert "Sums need a number column" in rejected.json()["detail"]


async def test_audits_are_filtered_paged_and_exported_without_a_row_limit(api, model_answer):
    await api.put(
        "/v1/workflows/wf-a",
        json=invoice_workflow(rule("t", condition("total_amount", "==", "1"))),
    )
    await api.put("/v1/workflows/wf-b", json={**invoice_workflow(), "name": "Receipts"})
    failed = [
        await run(api, model_answer, {"total_amount": 2}, workflow_id="wf-a") for _ in range(3)
    ]
    passed = await run(api, model_answer, {"total_amount": 1}, workflow_id="wf-b")

    page = (await api.get("/v1/audits", params={"limit": 2})).json()
    assert (page["total"], len(page["audits"])) == (4, 2)
    assert (await api.get("/v1/audits", params={"outcome": "passed"})).json()["total"] == 1
    # "review" is every run a person must look at: rejected or flagged.
    assert (await api.get("/v1/audits", params={"outcome": "review"})).json()["total"] == 3
    by_name = (await api.get("/v1/audits", params={"q": "receipt"})).json()
    assert [a["id"] for a in by_name["audits"]] == [passed]
    by_workflow = (await api.get("/v1/audits", params={"workflowId": "wf-a"})).json()
    assert by_workflow["total"] == 3
    today = datetime.now(UTC).date().isoformat()
    assert (await api.get("/v1/audits", params={"day": today})).json()["total"] == 4
    assert (await api.get("/v1/audits", params={"day": "2001-01-01"})).json()["total"] == 0

    export = await api.get("/v1/audits/export.csv", params={"workflowId": "wf-a"})
    assert export.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(export.text.lstrip("﻿"))))
    assert rows[0][:2] == ["id", "outcome"]
    assert sorted(r[0] for r in rows[1:]) == sorted(failed)

    report = await api.get(f"/v1/audits/{failed[0]}/export.csv")
    lines = list(csv.reader(io.StringIO(report.text.lstrip("﻿"))))
    assert lines[0] == ["section", "document", "name", "value", "type", "status", "detail"]
    assert ["field", "Invoice", "total_amount", "2", "number", "flagged", ""] in lines
    assert any(line[0] == "rule" and line[5] == "failed" for line in lines)


async def test_csv_cells_never_run_as_formulas(api, model_answer):
    await api.put("/v1/workflows/wf-a", json={**invoice_workflow(), "name": "=HYPERLINK(1)"})
    await run(api, model_answer, {}, workflow_id="wf-a")
    export = (await api.get("/v1/audits/export.csv")).text
    assert "'=HYPERLINK(1)" in export
    assert runs._csv_line(["  =HYPERLINK(2)", "a-b", 3]).startswith("'  =HYPERLINK(2),a-b,3")


async def test_files_are_deleted_when_the_run_cannot_be_saved(api, monkeypatch):
    await api.put("/v1/workflows/wf-a", json=invoice_workflow())

    async def refuse(*_args, **_kwargs):
        raise RuntimeError("database down")

    from sqlalchemy.ext.asyncio import AsyncSession

    monkeypatch.setattr(AsyncSession, "commit", refuse)
    with pytest.raises(RuntimeError):
        await api.post("/v1/workflows/wf-a/runs", files=FILE)
    assert get_store().objects == {}  # type: ignore[attr-defined]


async def test_retention_deletes_old_runs_and_their_files(api, model_answer, monkeypatch):
    await api.put("/v1/workflows/wf-a", json=invoice_workflow())
    old, recent = (
        await run(api, model_answer, {}, workflow_id="wf-a"),
        await run(api, model_answer, {}, workflow_id="wf-a"),
    )
    async with db.session_factory() as session:
        await session.execute(
            update(Run)
            .where(Run.id == old)
            .values(created_at=datetime.now(UTC) - timedelta(days=40))
        )
        await session.commit()
    store = get_store().objects  # type: ignore[attr-defined]
    assert f"runs/{old}/0" in store

    assert await purge_expired() == 0  # retention off by default
    monkeypatch.setattr(get_settings(), "run_retention_days", 30)
    assert await purge_expired() == 1
    async with db.session_factory() as session:
        remaining = await session.scalars(select(Run.id))
        assert list(remaining) == [recent]
        assert await session.scalar(select(func.count()).select_from(Run)) == 1
    assert f"runs/{old}/0" not in store
    assert f"runs/{recent}/0" in store


async def test_progress_steps_are_data_not_text(api, model_answer):
    await api.put(
        "/v1/workflows/wf-a",
        json=invoice_workflow(rule("t", condition("total_amount", "EXISTS"))),
    )
    run_id = await run(api, model_answer, {"total_amount": 1}, workflow_id="wf-a")
    steps = (await api.get(f"/v1/runs/{run_id}")).json()["progress"]["steps"]
    assert [s["kind"] for s in steps] == ["queue", "model", "extract", "rules", "finalize"]
    assert steps[2]["documentType"] == "Invoice"
    assert steps[2]["fieldsExtracted"] == 1
    assert steps[3]["ruleCount"] == 1
    assert all("label" not in s for s in steps)


async def test_catalog(api):
    catalog = (await api.get("/v1/catalog")).json()
    types = {t["value"]: t for t in catalog["templateTypes"]}
    assert types["number"] == {"value": "number", "group": "common", "listable": True}
    assert types["object-array"]["listable"] is False
    assert catalog["tableType"] == "object-array"
    assert set(catalog["numberTypes"]) == {"integer", "number"}


async def test_a_report_shows_the_pages_of_its_documents(api, model_answer):
    await api.put("/v1/workflows/wf-a", json=invoice_workflow())
    run_id = await run(api, model_answer, {"total_amount": 1}, workflow_id="wf-a")
    document = (await api.get(f"/v1/audits/{run_id}")).json()["documents"][0]["id"]

    page = await api.get(f"/v1/runs/{run_id}/documents/{document}/pages/1")
    assert page.status_code == 200
    assert page.headers["content-type"] == "image/webp"
    assert page.content[8:12] == b"WEBP"
    assert (await api.get(f"/v1/runs/{run_id}/documents/{document}/pages/2")).status_code == 404
    assert (await api.get(f"/v1/runs/{run_id}/documents/doc-x/pages/1")).status_code == 404


async def test_the_dashboard_counts_outcomes_hours_and_documents(api, model_answer):
    await api.put(
        "/v1/workflows/wf-a",
        json=invoice_workflow(rule("total", condition("total_amount", "==", "1"))),
    )
    for answer in ({"total_amount": 2}, {"total_amount": 2, "tva": 4}, {"total_amount": 1}):
        await run(api, model_answer, answer, workflow_id="wf-a")

    board = (await api.get("/v1/dashboard")).json()
    today = board["performanceSeries"][-1]
    assert len(board["performanceSeries"]) == 14
    assert (today["runs"], today["passed"], today["failed"]) == (3, 1, 2)
    assert board["sources"] == {"api": 0, "test": 3}
    assert board["documents"]["documents"] == 3
    assert board["documents"]["pages"] == 3
    assert board["documents"]["byType"][0]["documentType"] == "Invoice"
    assert sum(h["runs"] for h in board["hourly"]) == 3
    assert board["timing"]["medianMs"] > 0
    activity = next(a for a in board["workflowActivity"] if a["workflowId"] == "wf-a")
    assert activity["runs"][-1] == 3
    assert len(activity["runs"]) == 7
