"""Client companies are kept apart, and runs are metered and paid for with credits."""

import io
from collections.abc import AsyncIterator, Callable

import pypdfium2 as pdfium
import pytest
from httpx import ASGITransport, AsyncClient

from repody.api.deps import optional_user
from repody.app import execute
from repody.extraction import client as inference
from repody.infra.auth import User
from repody.main import create_app
from repody.settings import get_settings
from tests.files import FILE, PDF
from tests.integration.helpers import invoice_workflow

PAGES = len(pdfium.PdfDocument(io.BytesIO(PDF)))
ACME = User(subject="alice", roles=frozenset({"admin"}), client="client-acme")
GLOBEX = User(subject="gus", roles=frozenset({"admin"}), client="client-globex")
PLATFORM = User(subject="pat", roles=frozenset({"platform_admin"}))


@pytest.fixture
async def as_user(api: AsyncClient) -> AsyncIterator[Callable[[User | None], AsyncClient]]:
    clients: list[AsyncClient] = []

    def make(user: User | None) -> AsyncClient:
        app = create_app()
        app.dependency_overrides[optional_user] = lambda: user
        clients.append(AsyncClient(transport=ASGITransport(app=app), base_url="http://test"))
        return clients[-1]

    yield make
    for c in clients:
        await c.aclose()


@pytest.fixture
def enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "credits_enforced", True)


async def grant(platform: AsyncClient, account: str, amount: int) -> dict:
    response = await platform.post(
        f"/v1/admin/clients/{account}/credits", json={"amount": amount, "note": "trial"}
    )
    assert response.status_code == 201, response.text
    return response.json()


async def credits(client: AsyncClient) -> dict:
    return (await client.get("/v1/me")).json()["credits"]


async def test_a_client_never_sees_or_changes_another_clients_work(as_user, model_answer):
    acme, globex, platform = as_user(ACME), as_user(GLOBEX), as_user(PLATFORM)
    assert (await acme.put("/v1/workflows/wf-acme", json=invoice_workflow())).status_code == 200
    run = (await acme.post("/v1/workflows/wf-acme/runs", files=FILE)).json()["runId"]
    report = (await acme.get(f"/v1/audits/{run}")).json()
    doc = report["documents"][0]["id"]

    for path in (
        "/v1/workflows/wf-acme",
        f"/v1/runs/{run}",
        f"/v1/audits/{run}",
        f"/v1/audits/{run}/export.csv",
        f"/v1/runs/{run}/documents/{doc}/pages/1",
    ):
        assert (await globex.get(path)).status_code == 404, path
    assert (await globex.put("/v1/workflows/wf-acme", json=invoice_workflow())).status_code == 404
    assert (await globex.post("/v1/workflows/wf-acme/deploy")).status_code == 404
    assert (await globex.post("/v1/workflows/wf-acme/runs", files=FILE)).status_code == 404
    assert (await globex.delete("/v1/workflows/wf-acme")).status_code == 404
    assert (await globex.post("/v1/runs/" + run + "/cancel")).status_code == 404
    assert (await globex.get("/v1/workflows")).json()["workflows"] == []
    assert (await globex.get("/v1/audits")).json()["total"] == 0
    export = (await globex.get("/v1/audits/export.csv")).text
    assert run not in export
    dashboard = (await globex.get("/v1/dashboard")).json()
    assert dashboard["recentAudits"] == []
    assert dashboard["workflows"] == []
    assert sum(day["runs"] for day in dashboard["performanceSeries"]) == 0

    # Acme sees its own; the platform admin sees everyone's.
    assert (await acme.get("/v1/audits")).json()["total"] == 1
    assert (await platform.get(f"/v1/audits/{run}")).status_code == 200
    assert (await acme.get(f"/v1/runs/{run}/documents/{doc}/pages/1")).status_code == 200


async def test_shared_workflows_are_read_only_for_clients(api, as_user, model_answer):
    await api.put("/v1/workflows/wf-example", json=invoice_workflow())  # no account: shared
    acme = as_user(ACME)
    example = (await acme.get("/v1/workflows/wf-example")).json()
    assert example["readOnly"] is True
    assert (await acme.put("/v1/workflows/wf-example", json=invoice_workflow())).status_code == 403
    assert (await acme.post("/v1/workflows/wf-example/deploy")).status_code == 403
    assert (await acme.post("/v1/workflows/wf-example/runs", files=FILE)).status_code == 403
    copy = await acme.post("/v1/workflows/wf-example/duplicate", json={"name": "Mine"})
    assert copy.status_code == 201
    assert copy.json()["readOnly"] is False


async def test_runs_wait_for_credits_and_pay_the_pages_they_send(as_user, model_answer, enforced):
    acme, platform = as_user(ACME), as_user(PLATFORM)
    await acme.put("/v1/workflows/wf-acme", json=invoice_workflow())
    refused = await acme.post("/v1/workflows/wf-acme/runs", files=FILE)
    assert refused.status_code == 402
    assert "Contact us for credits" in refused.json()["detail"]

    assert (await grant(platform, "client-acme", 10))["balance"] == 10
    assert await credits(acme) == {
        "account": "client-acme",
        "balance": 10,
        "held": 0,
        "enforced": True,
        "low": True,  # under AUDIT_CREDIT_LOW_BALANCE (20)
    }
    assert (await acme.post("/v1/workflows/wf-acme/runs", files=FILE)).status_code == 202
    assert (await credits(acme))["balance"] == 10 - PAGES

    usage = (await acme.get("/v1/credits/usage")).json()["accounts"]
    assert usage == [
        {
            "account": "client-acme",
            "balance": 10 - PAGES,
            "held": 0,
            "granted": 10,
            "runs": 1,
            "pages": PAGES,
            "modelMs": usage[0]["modelMs"],
            "lastActivity": usage[0]["lastActivity"],
        }
    ]
    # Only a platform admin grants; a client admin reads their own account only.
    assert (
        await acme.post("/v1/admin/clients/client-acme/credits", json={"amount": 5})
    ).status_code == 403
    await grant(platform, "client-globex", 3)
    assert [a["account"] for a in (await acme.get("/v1/credits/usage")).json()["accounts"]] == [
        "client-acme"
    ]
    everyone = (await platform.get("/v1/credits/usage")).json()["accounts"]
    assert {a["account"] for a in everyone} == {"client-acme", "client-globex"}


async def test_api_key_runs_are_paid_by_the_workflows_client(api, as_user, model_answer, enforced):
    acme, platform = as_user(ACME), as_user(PLATFORM)
    await acme.put("/v1/workflows/wf-acme", json=invoice_workflow())
    key = (await acme.post("/v1/workflows/wf-acme/deploy")).json()["apiKey"]
    headers = {"Authorization": f"Bearer {key}"}
    anonymous = as_user(None)  # the API key alone, no user
    refused = await anonymous.post("/v1/workflows/wf-acme/runs", files=FILE, headers=headers)
    assert refused.status_code == 402
    await grant(platform, "client-acme", PAGES)
    started = await anonymous.post("/v1/workflows/wf-acme/runs", files=FILE, headers=headers)
    assert started.status_code == 202
    assert (await credits(acme))["balance"] == 0


async def test_a_retry_with_the_same_idempotency_key_runs_and_pays_once(
    as_user, model_answer, enforced
):
    acme, platform = as_user(ACME), as_user(PLATFORM)
    await acme.put("/v1/workflows/wf-acme", json=invoice_workflow())
    await grant(platform, "client-acme", 10)
    headers = {"Idempotency-Key": "upload-42"}
    first = await acme.post("/v1/workflows/wf-acme/runs", files=FILE, headers=headers)
    again = await acme.post("/v1/workflows/wf-acme/runs", files=FILE, headers=headers)
    assert first.status_code == again.status_code == 202
    assert first.json() == again.json()
    assert (await credits(acme))["balance"] == 10 - PAGES
    other = await acme.post(
        "/v1/workflows/wf-acme/runs", files=FILE, headers={"Idempotency-Key": "43"}
    )
    assert other.json() != first.json()


async def test_a_run_that_never_started_pays_nothing(as_user, model_answer, enforced, monkeypatch):
    acme, platform = as_user(ACME), as_user(PLATFORM)
    await acme.put("/v1/workflows/wf-acme", json=invoice_workflow())
    await grant(platform, "client-acme", 10)

    async def broken(_run_id: str) -> None:
        raise RuntimeError("worker lost")

    monkeypatch.setattr(execute, "_process", broken)
    run = (await acme.post("/v1/workflows/wf-acme/runs", files=FILE)).json()["runId"]
    assert (await acme.get(f"/v1/runs/{run}")).json()["status"] == "failed"
    assert await credits(acme) == {
        "account": "client-acme",
        "balance": 10,
        "held": 0,
        "enforced": True,
        "low": True,  # under AUDIT_CREDIT_LOW_BALANCE (20)
    }


async def test_a_model_failure_pays_the_estimate(as_user, model_answer, enforced, monkeypatch):
    """A document the model failed on (a timeout) may have kept the GPU busy all along."""
    acme, platform = as_user(ACME), as_user(PLATFORM)
    await acme.put("/v1/workflows/wf-acme", json=invoice_workflow())
    await grant(platform, "client-acme", 10)

    async def timeout(_request: dict) -> inference.Reply:
        raise TimeoutError

    monkeypatch.setattr(inference, "chat", timeout)
    run = (await acme.post("/v1/workflows/wf-acme/runs", files=FILE)).json()["runId"]
    assert (await acme.get(f"/v1/runs/{run}")).json()["status"] == "done"
    assert (await credits(acme))["balance"] == 10 - PAGES


async def test_without_enforcement_runs_are_metered_not_refused(as_user, model_answer):
    acme, platform = as_user(ACME), as_user(PLATFORM)
    await acme.put("/v1/workflows/wf-acme", json=invoice_workflow())
    assert (await acme.post("/v1/workflows/wf-acme/runs", files=FILE)).status_code == 202
    usage = (await platform.get("/v1/credits/usage")).json()["accounts"]
    assert [(a["account"], a["balance"], a["pages"]) for a in usage] == [
        ("client-acme", -PAGES, PAGES)
    ]


async def test_a_run_reads_at_most_the_pages_allowed(as_user, model_answer, monkeypatch):
    monkeypatch.setattr(get_settings(), "max_pages_per_run", 1)
    monkeypatch.setattr(get_settings(), "max_upload_files", 2)
    acme = as_user(ACME)
    workflow = invoice_workflow()
    workflow["documents"].append({**workflow["documents"][0], "id": "doc-2", "documentType": "B"})
    await acme.put("/v1/workflows/wf-acme", json=workflow)
    two = [
        ("files", ("a.pdf", PDF, "application/pdf")),
        ("files", ("b.pdf", PDF, "application/pdf")),
    ]
    refused = await acme.post("/v1/workflows/wf-acme/runs", files=two)
    assert refused.status_code == 422
    assert "at most 1" in refused.json()["detail"]


async def test_workflow_definitions_and_json_bodies_are_bounded(api, monkeypatch):
    deep: dict = {"name": "leaf"}
    for level in range(7):
        deep = {"name": f"level{level}", "templateType": "object", "children": [deep]}
    workflow = invoice_workflow()
    workflow["documents"][0]["schema"] = [deep]
    too_deep = await api.put("/v1/workflows/wf-deep", json=workflow)
    assert too_deep.status_code == 422
    assert "levels deep" in too_deep.text

    examples = [{"input": "x", "output": "{}"}] * 6
    workflow = invoice_workflow()
    workflow["documents"][0]["extractionIclExamples"] = examples
    assert (await api.put("/v1/workflows/wf-icl", json=workflow)).status_code == 422

    monkeypatch.setattr(get_settings(), "max_json_bytes", 1000)
    big = invoice_workflow()
    big["description"] = "x" * 2000
    assert (await api.put("/v1/workflows/wf-big", json=big)).status_code == 413


async def test_audit_search_matches_wildcards_literally(api, model_answer):
    await api.put("/v1/workflows/wf-a", json=invoice_workflow())
    await api.post("/v1/workflows/wf-a/runs", files=FILE)
    assert (await api.get("/v1/audits", params={"q": "Invoices"})).json()["total"] == 1
    assert (await api.get("/v1/audits", params={"q": "%"})).json()["total"] == 0
    assert (await api.get("/v1/audits", params={"q": "Inv_ices"})).json()["total"] == 0
