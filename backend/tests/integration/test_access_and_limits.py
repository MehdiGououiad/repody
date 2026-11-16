"""Who may do what, the limits a caller hits, and input the API refuses."""

import json
from collections.abc import AsyncIterator, Callable

import pytest
from alembic.config import Config
from httpx import ASGITransport, AsyncClient

from alembic import command
from repody.api.deps import optional_user
from repody.app import execute
from repody.infra.auth import User
from repody.main import create_app
from tests.conftest import BACKEND
from tests.files import FILE, PDF
from tests.integration.helpers import condition, document, invoice_workflow, rule


@pytest.fixture
async def as_user(api: AsyncClient) -> AsyncIterator[Callable[[User | None], AsyncClient]]:
    """Clients that call the app as a given user (None: no valid token), on the ``api``
    fixture's database and inline runs."""
    clients: list[AsyncClient] = []

    def make(user: User | None) -> AsyncClient:
        app = create_app()
        app.dependency_overrides[optional_user] = lambda: user
        clients.append(AsyncClient(transport=ASGITransport(app=app), base_url="http://test"))
        return clients[-1]

    yield make
    for c in clients:
        await c.aclose()


VIEWER = User(subject="vera", roles=frozenset({"viewer"}))


async def deploy(api: AsyncClient, workflow_id: str) -> dict[str, str]:
    await api.put(f"/v1/workflows/{workflow_id}", json=invoice_workflow())
    key = (await api.post(f"/v1/workflows/{workflow_id}/deploy")).json()["apiKey"]
    return {"Authorization": f"Bearer {key}"}


def test_the_migration_matches_the_models(database):
    """``alembic check``: autogenerate finds nothing to change, so models and schema agree."""
    config = Config(BACKEND / "alembic.ini")
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    command.check(config)


async def test_a_viewer_reads_but_cannot_change_or_run(api, as_user):
    await api.put("/v1/workflows/wf-a", json=invoice_workflow())
    viewer = as_user(VIEWER)
    assert (await viewer.get("/v1/workflows/wf-a")).status_code == 200
    assert (await viewer.put("/v1/workflows/wf-a", json=invoice_workflow())).status_code == 403
    assert (await viewer.delete("/v1/workflows/wf-a")).status_code == 403
    assert (await viewer.post("/v1/workflows/wf-a/runs", files=FILE)).status_code == 401
    assert (await viewer.get("/v1/dashboard")).status_code == 403
    assert (await viewer.post("/v1/runs/run-any/cancel")).status_code == 403


async def test_anonymous_callers_cannot_tell_which_workflows_exist(api, as_user):
    await api.put("/v1/workflows/wf-a", json=invoice_workflow())
    anonymous = as_user(None)
    known = await anonymous.post("/v1/workflows/wf-a/runs", files=FILE)
    unknown = await anonymous.post("/v1/workflows/wf-missing/runs", files=FILE)
    assert known.status_code == unknown.status_code == 401
    assert known.json() == unknown.json()


async def test_an_api_key_only_reads_its_own_workflow_runs(api, as_user, model_answer):
    key_a, key_b = await deploy(api, "wf-a"), await deploy(api, "wf-b")
    anonymous = as_user(None)
    started = await anonymous.post("/v1/workflows/wf-a/runs", files=FILE, headers=key_a)
    assert started.status_code == 202, started.text
    run_path = f"/v1/runs/{started.json()['runId']}"
    assert (await anonymous.get(run_path, headers=key_a)).status_code == 200
    assert (await anonymous.get(run_path, headers=key_b)).status_code == 401
    # Once the workflow is archived its key no longer works.
    await api.delete("/v1/workflows/wf-a")
    assert (await anonymous.get(run_path, headers=key_a)).status_code == 401


async def test_files_map_to_documents_by_id_or_type_one_each(api, model_answer):
    two_documents = invoice_workflow()
    two_documents["documents"].append(document("doc-po", "Purchase Order"))
    await api.put("/v1/workflows/wf-a", json=two_documents)
    files = [
        ("files", ("a.pdf", PDF, "application/pdf")),
        ("files", ("b.pdf", PDF, "application/pdf")),
    ]
    named = await api.post(
        "/v1/workflows/wf-a/runs", files=files, data={"documents": ["purchase order", "doc-inv"]}
    )
    assert named.status_code == 202, named.text
    report = (await api.get(f"/v1/audits/{named.json()['runId']}")).json()
    assert [d["documentType"] for d in report["documents"]] == ["Purchase Order", "Invoice"]
    twice = await api.post(
        "/v1/workflows/wf-a/runs", files=files, data={"documents": ["doc-inv", "Invoice"]}
    )
    assert twice.status_code == 422
    assert "more than one file" in twice.json()["detail"]


async def test_an_invalid_draft_definition_is_a_validation_error(api):
    await api.put("/v1/workflows/wf-a", json=invoice_workflow())
    bad = await api.post(
        "/v1/workflows/wf-a/runs", files=FILE, data={"definition": json.dumps({"rules": [{}]})}
    )
    assert bad.status_code == 422
    assert isinstance(bad.json()["detail"], list)  # FastAPI's validation errors, with locations


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda wf: wf.update(name="x" * 201), "at most 200 characters"),
        (
            lambda wf: wf["documents"][0]["schema"].append(
                {"id": "f3", "name": "Total Amount", "templateType": "number"}
            ),
            "duplicate field name",
        ),
        (
            lambda wf: wf["documents"][0]["schema"].append(
                {"id": "f3", "name": "kind", "templateType": "enum", "enumValues": ["only"]}
            ),
            "at least 2 choices",
        ),
    ],
)
async def test_saving_rejects_what_a_run_could_not_handle(api, change, message):
    workflow = invoice_workflow()
    change(workflow)
    saved = await api.put("/v1/workflows/wf-a", json=workflow)
    assert saved.status_code == 422
    assert message in saved.text


async def test_a_truncated_model_answer_is_an_extraction_error(api, model_answer):
    await api.put(
        "/v1/workflows/wf-a",
        json=invoice_workflow(rule("total", condition("total_amount", "==", "6000"))),
    )
    model_answer.update(text='{"total_amount": 6000, "tva": 10', truncated=True)
    started = await api.post("/v1/workflows/wf-a/runs", files=FILE)
    report = (await api.get(f"/v1/audits/{started.json()['runId']}")).json()
    document = report["documents"][0]
    assert "cut off" in document["extraction"]["error"]
    assert all(not f["extracted"] for f in document["fields"])  # nothing read from a cut answer
    assert report["ruleResults"][0]["status"] == "skipped"


async def test_a_failure_inside_the_worker_fails_the_run(api, model_answer, monkeypatch):
    await api.put("/v1/workflows/wf-a", json=invoice_workflow())

    async def broken(_run_id: str) -> None:
        raise RuntimeError("database went away")

    monkeypatch.setattr(execute, "_process", broken)
    started = await api.post("/v1/workflows/wf-a/runs", files=FILE)
    state = (await api.get(f"/v1/runs/{started.json()['runId']}")).json()
    assert state["status"] == "failed"
    assert state["error"] == execute.FAILURE_MESSAGE


async def test_me_says_what_each_caller_may_do(api, as_user):
    viewer = (await as_user(VIEWER).get("/v1/me")).json()
    assert viewer == {
        "roles": ["viewer"],
        "permissions": ["workflow:read", "run:read"],
        "withCredits": [],
        "credits": {"account": None, "balance": 0, "held": 0, "enforced": False, "low": False},
    }
    operator = (
        await as_user(User(subject="otto", roles=frozenset({"operator"}))).get("/v1/me")
    ).json()
    assert "workflow:deploy" in operator["permissions"]
    assert "workflow:delete" not in operator["permissions"]
    assert (await as_user(None).get("/v1/me")).json()["permissions"] == []
