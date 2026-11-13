from datetime import UTC, datetime, timedelta

from sqlalchemy import update

from repody.app.maintenance import fail_stuck_runs
from repody.infra import db
from repody.infra.models import Run


async def test_health_and_config(api):
    assert (await api.get("/v1/healthz/live")).json()["status"] == "ok"
    ready = (await api.get("/v1/healthz")).json()
    assert ready == {"status": "ok", "database": True, "redis": True, "oidcEnabled": False}
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

    async with db.session_factory() as session:
        await session.execute(
            update(Run)
            .where(Run.id == "AUD-2023-8902")
            .values(
                status="running",
                outcome=None,
                finished_at=None,
                started_at=datetime.now(UTC) - timedelta(hours=1),
            )
        )
        await session.commit()
    assert len(await fail_stuck_runs()) == 1
    state = (await api.get("/v1/runs/AUD-2023-8902")).json()
    assert state["status"] == "failed"
    assert "worker stopped" in state["error"]


async def test_maintenance_is_a_scheduled_task(api):
    from repody.app.maintenance import upkeep
    from repody.settings import get_settings
    from repody.worker import MAINTENANCE_TASK, broker, scheduler

    task = broker.find_task(MAINTENANCE_TASK)
    assert task is not None
    interval = get_settings().maintenance_interval_seconds
    assert task.labels["schedule"] == [{"interval": interval}]
    [source] = scheduler.sources
    await source.startup()  # the scheduler process does this when it starts
    schedules = await source.get_schedules()
    assert [s.task_name for s in schedules] == [MAINTENANCE_TASK]
    await upkeep()  # one pass on an empty database does nothing and does not fail


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


async def test_a_stuck_run_is_flagged_and_recovered_on_demand(api, seeded):
    await _make_running("AUD-2023-8902", started_hours_ago=2)
    [active] = (await api.get("/v1/operations")).json()["active"]
    assert active["stuck"] is True
    recovered = (await api.post("/v1/operations/recover")).json()
    assert recovered == {"failed": ["AUD-2023-8902"]}
    assert (await api.get("/v1/operations")).json()["active"] == []


async def test_a_run_is_cancelled_once_and_never_finishes_afterwards(api, seeded):
    await _make_running("AUD-2023-8902", started_hours_ago=0)
    assert (await api.get("/v1/operations")).json()["active"][0]["stuck"] is False
    assert (await api.post("/v1/runs/AUD-2023-8902/cancel")).status_code == 204
    state = (await api.get("/v1/runs/AUD-2023-8902")).json()
    assert state["status"] == "failed"
    assert state["error"] == "Cancelled by dev-local."
    again = await api.post("/v1/runs/AUD-2023-8902/cancel")
    assert again.status_code == 409
    assert (await api.post("/v1/runs/run-unknown/cancel")).status_code == 404
