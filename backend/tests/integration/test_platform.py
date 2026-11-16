from datetime import UTC, datetime, timedelta

from sqlalchemy import update

from repody.app.maintenance import upkeep
from repody.infra import db
from repody.infra.models import Run


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
