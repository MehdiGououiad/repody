"""Demo mode (the public playground): anonymous visitors see the shared examples and only their
own workflows, never another visitor's, and cannot run or publish (402: contact us)."""

import uuid
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import update

from repody.api.deps import CREDITS, VISITOR_HEADER
from repody.app.workflows import purge_visitor_workflows
from repody.infra import db
from repody.infra.models import Workflow
from repody.main import create_app
from repody.settings import Settings, get_settings
from tests.files import FILE
from tests.integration.helpers import invoice_workflow


@pytest.fixture
async def visitor(
    api: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[Callable[[], AsyncClient]]:
    """Demo mode on, with an example workflow (saved before, so it has no visitor); each call
    is a new visitor's browser (its own visitor id, as the web app's cookie)."""
    await api.put("/v1/workflows/wf-example", json=invoice_workflow())
    monkeypatch.setattr(get_settings(), "demo_mode", True)
    clients: list[AsyncClient] = []

    def make() -> AsyncClient:
        clients.append(
            AsyncClient(
                transport=ASGITransport(app=create_app()),
                base_url="http://test",
                headers={VISITOR_HEADER: str(uuid.uuid4())},
            )
        )
        return clients[-1]

    yield make
    for client in clients:
        await client.aclose()


def ids(response) -> set[str]:
    return {w["id"] for w in response.json()["workflows"]}


async def test_visitors_see_the_examples_and_only_their_own_workflows(visitor):
    alice, bob = visitor(), visitor()
    assert (await alice.put("/v1/workflows/wf-alice", json=invoice_workflow())).status_code == 200
    assert ids(await alice.get("/v1/workflows")) == {"wf-example", "wf-alice"}
    assert ids(await bob.get("/v1/workflows")) == {"wf-example"}
    assert {w["id"] for w in (await bob.get("/v1/dashboard")).json()["workflows"]} == {"wf-example"}
    # Bob cannot read, overwrite or delete Alice's workflow: to him it does not exist.
    assert (await bob.get("/v1/workflows/wf-alice")).status_code == 404
    assert (await bob.put("/v1/workflows/wf-alice", json=invoice_workflow())).status_code == 404
    assert (await bob.delete("/v1/workflows/wf-alice")).status_code == 404
    await bob.post("/v1/workflows/bulk-delete", json={"ids": ["wf-alice"]})
    assert (await alice.get("/v1/workflows/wf-alice")).status_code == 200


async def test_examples_are_read_only_and_duplicated_to_edit(visitor):
    alice = visitor()
    example = (await alice.get("/v1/workflows/wf-example")).json()
    assert example["readOnly"] is True
    assert (await alice.put("/v1/workflows/wf-example", json=invoice_workflow())).status_code == 403
    assert (await alice.delete("/v1/workflows/wf-example")).status_code == 403
    await alice.post("/v1/workflows/bulk-delete", json={"ids": ["wf-example"]})
    assert "wf-example" in ids(await alice.get("/v1/workflows"))

    copy = await alice.post("/v1/workflows/wf-example/duplicate", json={"name": "My invoices"})
    assert copy.status_code == 201
    mine = copy.json()
    assert (mine["name"], mine["readOnly"], mine["status"]) == ("My invoices", False, "draft")
    assert mine["documents"] == example["documents"]
    assert (
        await alice.put(f"/v1/workflows/{mine['id']}", json=invoice_workflow())
    ).status_code == 200


async def test_visitors_cannot_run_publish_or_stop_runs(visitor):
    alice = visitor()
    await alice.put("/v1/workflows/wf-alice", json=invoice_workflow())
    for response in [
        await alice.post("/v1/workflows/wf-alice/runs", files=FILE),
        await alice.post("/v1/workflows/wf-example/runs", files=FILE),
        await alice.post("/v1/workflows/wf-alice/deploy"),
        await alice.post("/v1/runs/run-any/cancel"),
    ]:
        assert (response.status_code, response.json()["detail"]) == (402, CREDITS)
    config = (await alice.get("/v1/platform/config")).json()
    # The public playground does not say where the model runs, nor wake it.
    assert (config["llamacppBaseUrl"], config["modelAvailable"]) == ("", None)


async def test_a_browser_without_a_visitor_id_is_nobody(visitor, api):
    assert (await api.get("/v1/workflows")).status_code == 401
    named = AsyncClient(
        transport=ASGITransport(app=create_app()),
        base_url="http://test",
        headers={VISITOR_HEADER: "not-a-uuid"},
    )
    async with named:
        assert (await named.get("/v1/workflows")).status_code == 401


async def test_a_visitor_keeps_a_limited_number_of_workflows(visitor, monkeypatch):
    monkeypatch.setattr(get_settings(), "demo_max_workflows", 2)
    alice = visitor()
    assert (await alice.post("/v1/workflows", json={"name": "One"})).status_code == 201
    assert (await alice.put("/v1/workflows/wf-two", json=invoice_workflow())).status_code == 200
    assert (await alice.post("/v1/workflows", json={"name": "Three"})).status_code == 409
    duplicate = await alice.post("/v1/workflows/wf-example/duplicate", json={"name": "Copy"})
    assert duplicate.status_code == 409
    # Saving one she already has is not a new one.
    assert (await alice.put("/v1/workflows/wf-two", json=invoice_workflow())).status_code == 200


async def test_maintenance_deletes_old_visitor_workflows_and_keeps_the_examples(visitor):
    alice = visitor()
    await alice.put("/v1/workflows/wf-old", json=invoice_workflow())
    await alice.put("/v1/workflows/wf-new", json=invoice_workflow())
    async with db.session_factory() as session:
        long_ago = datetime.now(UTC) - timedelta(days=get_settings().demo_retention_days + 1)
        await session.execute(
            update(Workflow)
            .where(Workflow.id.in_(["wf-old", "wf-example"]))
            .values(updated_at=long_ago)
        )
        assert await purge_visitor_workflows(session) == 1
        await session.commit()
    assert ids(await alice.get("/v1/workflows")) == {"wf-example", "wf-new"}


def test_demo_mode_is_a_deployment_of_its_own_without_sign_in():
    with pytest.raises(ValidationError, match="AUDIT_OIDC_ENABLED=false"):
        Settings(demo_mode=True, oidc_enabled=True, oidc_issuer="https://auth.example")
    # Production requires sign-in, so the playground can never be production itself.
    with pytest.raises(ValidationError, match="must be true in production"):
        Settings(demo_mode=True, deployment_environment="production")


async def test_a_visitor_is_offered_the_paid_actions(visitor):
    access = (await visitor().get("/v1/me")).json()
    assert "workflow:write" in access["permissions"]
    assert set(access["withCredits"]) == {"run:execute", "workflow:deploy"}
