import json

from repody.extraction import client
from repody.infra import queue
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


async def test_queue_cap_and_position(api, monkeypatch):
    async def keep_queued(_run_id: str) -> bool:
        return True

    monkeypatch.setattr(queue, "dispatch", keep_queued)
    monkeypatch.setattr(get_settings(), "max_queued_runs", 1)
    await deploy(api)
    first = await api.post("/v1/workflows/wf-run/runs")
    assert first.status_code == 202
    state = (await api.get(f"/v1/runs/{first.json()['runId']}")).json()
    assert state["status"] == "queued"
    assert state["progress"]["queuePosition"] == 1
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
    assert call["base_url"] is None  # the NuExtract server
    assert call["request"]["extra_body"]["chat_template_kwargs"]["mode"] == "markdown"


async def test_markdown_with_lightonocr(api, model_answer, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "markdown_provider", "lightonocr")
    model_answer["text"] = "# FACTURE"
    document = await run_markdown(api)
    assert document["extraction"]["markdownText"] == "# FACTURE"
    [call] = model_answer["calls"]  # one page, one request
    assert call["base_url"] == settings.lightonocr_base_url
    request = call["request"]
    assert request["model"] == settings.lightonocr_served_model
    assert (request["max_tokens"], request["temperature"], request["top_p"]) == (4096, 0.2, 0.9)
    assert [part["type"] for part in request["messages"][0]["content"]] == ["image_url"]
