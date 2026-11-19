import asyncio
from datetime import UTC, datetime, timedelta

from httpx import ASGITransport, AsyncClient
from sqlalchemy import update

from repody.api import platform as platform_api
from repody.api.deps import optional_user
from repody.app.maintenance import upkeep
from repody.infra import db
from repody.infra.auth import User
from repody.infra.models import Run
from repody.main import create_app


async def test_health_and_config(api):
    assert (await api.get("/v1/healthz/live")).json()["status"] == "ok"
    ready = (await api.get("/v1/healthz")).json()
    assert ready == {"status": "ok", "database": True, "oidcEnabled": False}
    config = (await api.get("/v1/platform/config")).json()
    assert config["modelAvailable"] is False  # no llama-server in tests


async def test_dashboard_and_maintenance(api, seeded):
    dashboard = (await api.get("/v1/dashboard")).json()
    kpis = [k["id"] for k in dashboard["kpis"]]
    assert kpis == ["auditsWeek", "passRate", "failures"]
    assert dashboard["recentAudits"][0]["id"] == "AUD-2023-8902"
    assert dashboard["failedAudits"][0]["id"] == "AUD-2023-8902"
    assert dashboard["performanceSeries"][-1]["day"] == datetime.now(UTC).date().isoformat()
    assert dashboard["workflows"][0]["id"] == "wf-invoice-audit"
    await upkeep()  # one maintenance pass keeps what is within retention
    assert (await api.get("/v1/audits")).json()["total"] == 1


async def test_the_control_room_shows_runs_in_flight_and_failures(api, seeded):
    async with db.session_factory() as session:
        await session.execute(
            update(Run)
            .where(Run.id == "AUD-2023-8902")
            .values(
                status="failed", outcome=None, error="Model timed out", created_at=datetime.now(UTC)
            )
        )
        await session.commit()
    ops = (await api.get("/v1/operations")).json()
    assert ops["errors"][0]["id"] == "AUD-2023-8902"
    assert ops["errors"][0]["error"] == "Model timed out"
    assert len(ops["throughput"]) == 24
    assert set(ops["queue"]) == {"queuedRuns", "runningRuns"}
    assert isinstance(ops["active"], list)


async def _make_running(run_id: str, started_hours_ago: float) -> None:
    async with db.session_factory() as session:
        await session.execute(
            update(Run)
            .where(Run.id == run_id)
            .values(
                status="running",
                outcome=None,
                finished_at=None,
                started_at=datetime.now(UTC) - timedelta(hours=started_hours_ago),
            )
        )
        await session.commit()


async def test_a_run_is_cancelled_once_and_never_finishes_afterwards(api, seeded, cancelled):
    await _make_running("AUD-2023-8902", started_hours_ago=0)
    assert (await api.post("/v1/runs/AUD-2023-8902/cancel")).status_code == 204
    state = (await api.get("/v1/runs/AUD-2023-8902")).json()
    assert state["status"] == "failed"
    assert state["error"] == "Cancelled by dev-local."
    assert cancelled == []  # the seeded run never went through Hatchet
    again = await api.post("/v1/runs/AUD-2023-8902/cancel")
    assert again.status_code == 409
    assert (await api.post("/v1/runs/run-unknown/cancel")).status_code == 404


async def test_model_wake_starts_in_background_with_cooldown_and_requires_permission(
    api, model_answer, monkeypatch
):
    monkeypatch.setattr(platform_api, "_last_wake", None)

    first = await api.post("/v1/model/wake")
    assert first.status_code == 202
    if platform_api._wake_tasks:
        await asyncio.gather(*platform_api._wake_tasks)
    assert model_answer["wakes"] == 1

    # Second call within the 60 s cooldown returns 202 without waking again.
    second = await api.post("/v1/model/wake")
    assert second.status_code == 202
    if platform_api._wake_tasks:
        await asyncio.gather(*platform_api._wake_tasks)
    assert model_answer["wakes"] == 1

    # A viewer (no run:execute permission) is refused with 403.
    app = create_app()
    app.dependency_overrides[optional_user] = lambda: User(
        subject="vera", roles=frozenset({"viewer"})
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as viewer:
        assert (await viewer.post("/v1/model/wake")).status_code == 403
