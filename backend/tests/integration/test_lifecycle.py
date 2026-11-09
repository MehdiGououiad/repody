"""The run and workflow lifecycles (repody.app.lifecycle, docs/LIFECYCLES.md)."""

import pytest
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from tests.integration.helpers import invoice_workflow

from repody.app.lifecycle import RUN_TRANSITIONS, move_run
from repody.app.runs import fail_run
from repody.app.seed import seed
from repody.infra import db
from repody.infra.models import Run, Workflow

SEED_RUN = "AUD-2023-8902"  # a done run


def test_done_and_failed_are_final():
    assert RUN_TRANSITIONS["done"] == RUN_TRANSITIONS["failed"] == ()
    assert set(RUN_TRANSITIONS["queued"]) == {"running", "failed"}
    assert set(RUN_TRANSITIONS["running"]) == {"done", "failed"}


async def test_a_final_run_never_moves(api):
    async with db.session_factory() as session:
        await seed(session)
        await session.commit()
    async with db.session_factory() as session:
        for to in ("running", "done", "failed"):
            assert await move_run(session, SEED_RUN, to) is False
        with pytest.raises(ValueError, match="cannot go from done to failed"):
            await move_run(session, SEED_RUN, "failed", only_from="done")
    assert await fail_run(SEED_RUN, "late failure") is False
    assert (await api.get(f"/v1/runs/{SEED_RUN}")).json()["status"] == "done"


async def test_the_database_rejects_impossible_states(api):
    async with db.session_factory() as session:
        await seed(session)
        await session.commit()
    impossible = [
        (Run, Run.id == SEED_RUN, {"status": "paused"}),
        (Run, Run.id == SEED_RUN, {"status": "failed"}),  # failed runs have no outcome
        (Workflow, Workflow.id == "wf-invoice-audit", {"status": "draft"}),  # it is deployed
    ]
    for table, where, values in impossible:
        async with db.session_factory() as session:
            with pytest.raises(IntegrityError):
                await session.execute(update(table).where(where).values(**values))


async def test_the_server_owns_the_workflow_status(api):
    created = (await api.post("/v1/workflows", json={"name": "Draft"})).json()
    path = f"/v1/workflows/{created['id']}"
    # A client cannot make a workflow active by saving it: only deploying does.
    saved = (await api.put(path, json={**invoice_workflow(), "status": "active"})).json()
    assert saved["status"] == "draft" and saved["deployedAt"] is None

    deployed = (await api.post(f"{path}/deploy")).json()
    assert deployed["status"] == "active" and deployed["apiKey"]
    saved = (await api.put(path, json={**invoice_workflow(), "status": "draft"})).json()
    assert saved["status"] == "active"  # saving the definition keeps it deployed

    assert (await api.delete(path)).status_code == 204
    assert (await api.put(path, json=invoice_workflow())).status_code == 404  # archived
    assert (await api.get(path)).status_code == 404
