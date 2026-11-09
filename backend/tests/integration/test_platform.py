from datetime import UTC, datetime, timedelta

from sqlalchemy import update

from repody.app.maintenance import fail_stuck_runs
from repody.app.seed import seed
from repody.infra import db
from repody.infra.models import Run


async def test_health_and_config(api):
    assert (await api.get("/v1/healthz/live")).json()["status"] == "ok"
    ready = (await api.get("/v1/healthz")).json()
    assert ready == {"status": "ok", "database": True, "redis": True, "oidcEnabled": False}
    config = (await api.get("/v1/platform/config")).json()
    assert config["modelAvailable"] is False  # no llama-server in tests


async def test_dashboard_and_maintenance(api):
    async with db.session_factory() as session:
        await seed(session)
        await session.commit()
    dashboard = (await api.get("/v1/dashboard")).json()
    kpis = [k["id"] for k in dashboard["kpis"]]
    assert kpis == ["auditsWeek", "passRate", "failures", "pendingReview"]
    assert dashboard["audits"][0]["id"] == "AUD-2023-8902"
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
    assert await fail_stuck_runs() == 1
    state = (await api.get("/v1/runs/AUD-2023-8902")).json()
    assert state["status"] == "failed"
    assert "worker stopped" in state["error"]


async def test_one_replica_does_the_upkeep_per_interval(api):
    from repody.app.maintenance import _claim_turn
    from repody.infra.redis import get_redis

    await get_redis().delete("repody:maintenance")
    assert await _claim_turn(60) is True
    assert await _claim_turn(60) is False  # another replica in the same interval skips
