import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import update

from repody.app import execute, maintenance
from repody.app.lifecycle import QUEUE_TIMEOUT, STUCK, STUCK_MARGIN, move_run
from repody.extraction import client
from repody.infra import db, queue
from repody.infra.models import Run
from repody.settings import get_settings
from tests.files import FILE, PDF
from tests.integration.helpers import condition, invoice_workflow, rule


async def deploy(api, *rules) -> dict[str, str]:
    await api.put("/v1/workflows/wf-run", json=invoice_workflow(*rules))
    key = (await api.post("/v1/workflows/wf-run/deploy")).json()["apiKey"]
    return {"Authorization": f"Bearer {key}"}


async def test_api_run_extracts_and_checks_rules(api, model_answer):
    auth = await deploy(
        api,
        rule("total", condition("total_amount", "==", "6000")),
        rule("tva", condition("tva", "<", "500"), severity="flag"),
    )
    model_answer["text"] = json.dumps({"total_amount": 6000, "tva": 1000})
    started = await api.post("/v1/workflows/wf-run/runs", files=FILE, headers=auth)
    assert started.status_code == 202, started.text
    run_id = started.json()["runId"]

    state = (await api.get(f"/v1/runs/{run_id}", headers=auth)).json()
    assert state["status"] == "done"
    report = state["result"]
    assert report["status"] == "warning"  # only the flag rule failed
    assert report["source"] == "api"
    assert [r["status"] for r in report["ruleResults"]] == ["passed", "failed"]
    fields = {f["key"]: f for f in report["documents"][0]["fields"]}
    assert fields["total_amount"]["value"] == 6000
    assert not fields["total_amount"]["flagged"]
    assert fields["tva"]["flagged"]
    assert report["summary"] == {"total": 2, "passed": 1, "failed": 1, "fieldsExtracted": 2}
    assert all(step["status"] == "done" for step in state["progress"]["steps"])

    audits = (await api.get("/v1/audits")).json()
    assert audits["total"] == 1
    assert (await api.get(f"/v1/audits/{run_id}")).json()["id"] == run_id


async def test_a_sleeping_model_is_a_step_of_its_own(api, model_answer):
    auth = await deploy(api)
    model_answer["text"] = json.dumps({"total_amount": 6000})
    for asleep in (True, False):
        model_answer["asleep"] = asleep
        started = await api.post("/v1/workflows/wf-run/runs", files=FILE, headers=auth)
        steps = (await api.get(f"/v1/runs/{started.json()['runId']}", headers=auth)).json()[
            "progress"
        ]["steps"]
        assert [s["kind"] for s in steps] == ["queue", "model", "extract", "finalize"]
        assert steps[1]["status"] == "done"
        assert steps[1]["coldStart"] is asleep


async def test_test_run_uses_the_posted_draft(api, model_answer):
    await deploy(api)
    draft = invoice_workflow(rule("total", condition("total_amount", "==", "1")))
    model_answer["text"] = json.dumps({"total_amount": 6000})
    started = await api.post(
        "/v1/workflows/wf-run/runs",
        files=FILE,
        data={"documents": "Invoice", "definition": json.dumps(draft)},
    )
    report = (await api.get(f"/v1/runs/{started.json()['runId']}")).json()["result"]
    assert report["source"] == "test"
    assert report["status"] == "failed"


async def test_extraction_error_is_on_the_report_and_skips_rules(api, monkeypatch):
    async def broken(_payload, **_servers):
        raise RuntimeError("llama-server is down")

    monkeypatch.setattr(client, "chat", broken)
    await deploy(api, rule("total", condition("total_amount", "==", "6000")))
    started = await api.post("/v1/workflows/wf-run/runs", files=FILE)
    state = (await api.get(f"/v1/runs/{started.json()['runId']}")).json()
    report = state["result"]
    assert report["ruleResults"][0]["status"] == "skipped"
    assert report["documents"][0]["fields"] == []
    assert report["documents"][0]["extraction"]["error"].startswith("Extraction failed")
    extract = next(s for s in state["progress"]["steps"] if s["kind"] == "extract")
    assert extract["failed"] is True


async def test_unreadable_answer_is_reported(api, model_answer):
    await deploy(api)
    model_answer["text"] = "Sorry, I cannot read this document."
    started = await api.post("/v1/workflows/wf-run/runs", files=FILE)
    report = (await api.get(f"/v1/runs/{started.json()['runId']}")).json()["result"]
    assert (
        report["documents"][0]["extraction"]["error"] == "The model's answer is not a JSON object."
    )


async def test_run_input_errors(api):
    auth = await deploy(api)
    text_file = await api.post(
        "/v1/workflows/wf-run/runs",
        files={"files": ("a.txt", b"hello", "text/plain")},
        headers=auth,
    )
    assert text_file.status_code == 422
    assert "unsupported file type" in text_file.json()["detail"]
    unknown = await api.post(
        "/v1/workflows/wf-run/runs", files=FILE, data={"documents": "Receipt"}, headers=auth
    )
    assert unknown.status_code == 422
    two_files = [
        ("files", ("a.pdf", PDF, "application/pdf")),
        ("files", ("b.pdf", PDF, "application/pdf")),
    ]
    too_many = await api.post("/v1/workflows/wf-run/runs", files=two_files, headers=auth)
    assert too_many.status_code == 422
    assert (await api.get("/v1/runs/AUD-missing")).status_code == 404


async def test_wrong_api_key_is_refused_when_signed_in_users_are_required(api, monkeypatch):
    await deploy(api)
    monkeypatch.setattr(get_settings(), "oidc_enabled", True)
    refused = await api.post(
        "/v1/workflows/wf-run/runs", files=FILE, headers={"Authorization": "Bearer wrong"}
    )
    assert refused.status_code == 401


async def test_an_unknown_caller_uploads_nothing(api, monkeypatch):
    """The caller is checked from the headers: the body of a refused request is never read."""
    await deploy(api)
    monkeypatch.setattr(get_settings(), "oidc_enabled", True)
    read = 0

    async def body():
        nonlocal read
        for _ in range(64):
            read += 1
            yield b"x" * 65536

    refused = await api.post(
        "/v1/workflows/wf-run/runs",
        content=body(),
        headers={
            "Authorization": "Bearer wrong",
            "Content-Type": "multipart/form-data; boundary=b",
        },
    )
    assert refused.status_code == 401
    assert read <= 1


async def test_bodies_are_limited_as_they_arrive(api, monkeypatch):
    """A declared length over the limit, and a chunked body that grows past it, are both 413."""
    auth = await deploy(api)
    monkeypatch.setattr(get_settings(), "max_request_bytes", 1000)
    monkeypatch.setattr(get_settings(), "max_upload_bytes", 1000)
    declared = await api.post("/v1/workflows/wf-run/runs", files=FILE, headers=auth)
    assert declared.status_code == 413

    async def chunks():
        yield (
            b"--b\r\nContent-Disposition: form-data; name=files; filename=a.pdf\r\n"
            b"Content-Type: application/pdf\r\n\r\n"
        )
        for _ in range(4):
            yield b"x" * 600

    chunked = await api.post(
        "/v1/workflows/wf-run/runs",
        content=chunks(),
        headers={**auth, "Content-Type": "multipart/form-data; boundary=b"},
    )
    assert chunked.status_code == 413
    monkeypatch.setattr(get_settings(), "max_json_bytes", 1000)
    workflow = invoice_workflow()
    workflow["description"] = "x" * 2000
    body = json.dumps(workflow).encode()

    async def json_chunks():
        yield body[:500]
        yield body[500:]

    streamed = await api.put(
        "/v1/workflows/wf-run", content=json_chunks(), headers={"Content-Type": "text/plain"}
    )
    assert streamed.status_code == 413


async def test_queue_cap_and_position(api, monkeypatch):
    async def keep_queued(_run_id: str, _client_key: str) -> str:
        return "task"

    monkeypatch.setattr(queue, "dispatch", keep_queued)
    monkeypatch.setattr(get_settings(), "max_queued_runs", 1)
    await deploy(api)
    first = await api.post("/v1/workflows/wf-run/runs")
    assert first.status_code == 202
    state = (await api.get(f"/v1/runs/{first.json()['runId']}")).json()
    assert state["status"] == "queued"
    second = await api.post("/v1/workflows/wf-run/runs")
    assert second.status_code == 503
    assert second.headers["retry-after"] == "15"


def markdown_workflow() -> dict:
    """One document without fields: it is transcribed to Markdown."""
    return {
        "name": "Scans",
        "documents": [{"id": "doc-scan", "documentType": "Scan", "markdownExtraction": True}],
    }


async def run_markdown(api) -> dict:
    await api.put("/v1/workflows/wf-md", json=markdown_workflow())
    started = await api.post("/v1/workflows/wf-md/runs", files=FILE)
    return (await api.get(f"/v1/runs/{started.json()['runId']}")).json()["result"]["documents"][0]


async def test_markdown_with_nuextract(api, model_answer):
    model_answer["text"] = "# FACTURE"
    document = await run_markdown(api)
    assert document["extraction"]["markdownText"] == "# FACTURE"
    [call] = model_answer["calls"]
    assert call["request"]["extra_body"]["chat_template_kwargs"]["mode"] == "markdown"


async def test_a_queue_that_cannot_take_the_run_fails_it_at_once(api, monkeypatch):
    async def down(_run_id: str, _client_key: str) -> str:
        raise ConnectionError("Hatchet is not answering")

    monkeypatch.setattr(queue, "dispatch", down)
    await deploy(api)
    refused = await api.post("/v1/workflows/wf-run/runs")
    assert refused.status_code == 503
    [audit] = (await api.get("/v1/operations")).json()["errors"]
    assert audit["error"] == "The run could not be queued."


async def test_hatchet_giving_up_fails_the_run_where_it_stopped(api, monkeypatch):
    async def keep_queued(_run_id: str, _client_key: str) -> str:
        return "task"

    monkeypatch.setattr(queue, "dispatch", keep_queued)
    await deploy(api)
    waiting = (await api.post("/v1/workflows/wf-run/runs")).json()["runId"]
    await execute.fail_unfinished(waiting)  # schedule timeout: never started
    state = (await api.get(f"/v1/runs/{waiting}")).json()
    assert (state["status"], state["error"]) == (
        "failed",
        "The run waited too long for a worker to start it.",
    )

    started = (await api.post("/v1/workflows/wf-run/runs")).json()["runId"]
    async with db.session_factory() as session:
        await move_run(session, started, "running", started_at=datetime.now(UTC))
        await session.commit()
    await execute.fail_unfinished(started)  # execution timeout or a lost worker
    state = (await api.get(f"/v1/runs/{started}")).json()
    assert state["status"] == "failed"
    assert state["error"].startswith("The run stopped before it finished")


async def test_stopping_a_run_cancels_its_hatchet_run(api, monkeypatch, cancelled):
    async def keep_queued(_run_id: str, _client_key: str) -> str:
        return "task-hatchet-1"

    monkeypatch.setattr(queue, "dispatch", keep_queued)
    await deploy(api)
    run_id = (await api.post("/v1/workflows/wf-run/runs")).json()["runId"]
    assert (await api.post(f"/v1/runs/{run_id}/cancel")).status_code == 204
    assert cancelled == ["task-hatchet-1"]


async def test_a_run_whose_worker_died_starts_over_on_the_next(api, model_answer, monkeypatch):
    """Hatchet gives a dead worker's task to another worker: the run is still running, and the
    new delivery runs it to the end instead of leaving it running for ever."""

    async def keep_queued(_run_id: str, _client_key: str) -> str:
        return "task"

    monkeypatch.setattr(queue, "dispatch", keep_queued)
    auth = await deploy(api)
    model_answer["text"] = json.dumps({"total_amount": 6000})
    run_id = (await api.post("/v1/workflows/wf-run/runs", files=FILE, headers=auth)).json()["runId"]
    async with db.session_factory() as session:  # the first worker took it, then died
        await move_run(session, run_id, "running", started_at=datetime.now(UTC))
        await session.commit()

    await execute.process_run(run_id)  # the same task, delivered again
    assert (await api.get(f"/v1/runs/{run_id}", headers=auth)).json()["status"] == "done"
    await execute.process_run(run_id)  # a finished run is never taken again
    assert len(model_answer["calls"]) == 1


async def test_maintenance_fails_the_runs_the_queue_lost(api, monkeypatch):
    async def lost(_run_id: str, _client_key: str) -> str:
        return "task"

    monkeypatch.setattr(queue, "dispatch", lost)
    await deploy(api)
    queued, running, recent = [
        (await api.post("/v1/workflows/wf-run/runs")).json()["runId"] for _ in range(3)
    ]
    long_ago = datetime.now(UTC) - QUEUE_TIMEOUT - STUCK_MARGIN - timedelta(minutes=1)
    async with db.session_factory() as session:
        await session.execute(update(Run).where(Run.id == queued).values(created_at=long_ago))
        await move_run(session, running, "running", started_at=long_ago)
        await session.commit()

    await maintenance.upkeep()
    states = {
        run_id: (await api.get(f"/v1/runs/{run_id}")).json() for run_id in (queued, running, recent)
    }
    assert [states[r]["status"] for r in (queued, running, recent)] == [
        "failed",
        "failed",
        "queued",
    ]
    assert states[queued]["error"] == STUCK


async def test_a_run_that_keeps_losing_its_worker_fails_at_its_time_limit(
    api, model_answer, monkeypatch
):
    """A document that kills its worker (out of memory) would be delivered again and again:
    every attempt counts from the run's first start, so it fails at the time limit."""

    async def keep_queued(_run_id: str, _client_key: str) -> str:
        return "task"

    monkeypatch.setattr(queue, "dispatch", keep_queued)
    await deploy(api)
    run_id = (await api.post("/v1/workflows/wf-run/runs", files=FILE)).json()["runId"]
    first_start = datetime.now(UTC) - timedelta(minutes=get_settings().run_timeout_minutes + 1)
    async with db.session_factory() as session:
        await move_run(session, run_id, "running", started_at=first_start)
        await session.commit()

    await execute.process_run(run_id)  # delivered again, past the limit
    state = (await api.get(f"/v1/runs/{run_id}")).json()
    assert state["status"] == "failed"
    assert state["error"].startswith("The run stopped before it finished")
    assert model_answer["calls"] == []


async def test_a_reject_rule_the_model_gave_no_value_for_sends_the_run_to_review(api, model_answer):
    """Never green on a check that did not happen: the total was not read, so its rule is
    skipped, and the run needs a person."""
    auth = await deploy(
        api,
        rule("total", condition("total_amount", "==", "6000")),
        rule("tva", condition("tva", "<", "500"), severity="flag"),
    )
    model_answer["text"] = json.dumps({"total_amount": None, "tva": 100})
    started = await api.post("/v1/workflows/wf-run/runs", files=FILE, headers=auth)
    report = (await api.get(f"/v1/runs/{started.json()['runId']}", headers=auth)).json()["result"]
    assert [r["status"] for r in report["ruleResults"]] == ["skipped", "passed"]
    assert report["status"] == "warning"
    # The report and the list say why: the field to look for, and the rule not checked.
    fields = {f["key"]: f["flagged"] for f in report["documents"][0]["fields"]}
    assert fields == {"total_amount": True, "tva": False}
    [audit] = (await api.get("/v1/audits")).json()["audits"]
    assert (audit["firstFailedRule"], audit["uncheckedRule"]) == (None, "total")


async def test_a_document_too_large_for_the_model_is_refused_before_it_runs(
    api, model_answer, monkeypatch
):
    auth = await deploy(api)
    monkeypatch.setattr(get_settings(), "inference_context_tokens", 2_000)
    refused = await api.post("/v1/workflows/wf-run/runs", files=FILE, headers=auth)
    assert refused.status_code == 422
    assert "tokens for the model" in refused.json()["detail"]
    assert model_answer["calls"] == []
    assert (await api.get("/v1/operations")).json()["queue"]["queuedRuns"] == 0

    monkeypatch.setattr(get_settings(), "inference_context_tokens", 131_072)
    started = await api.post("/v1/workflows/wf-run/runs", files=FILE, headers=auth)
    assert started.status_code == 202
