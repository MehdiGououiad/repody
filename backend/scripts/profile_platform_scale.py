"""Verbose platform scale profiler — SQL, admission, queue, outbox, live enqueue.

Usage (Postgres + Redis up; API for --live):

  node scripts/backend-run.mjs --dev python scripts/profile_platform_scale.py
  node scripts/backend-run.mjs --dev python scripts/profile_platform_scale.py --live
  node scripts/backend-run.mjs --dev python scripts/profile_platform_scale.py --live --seed-queue 200
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx


@dataclass
class Sample:
    name: str
    samples_ms: list[float] = field(default_factory=list)

    def add(self, ms: float) -> None:
        self.samples_ms.append(ms)

    def report(self) -> str:
        if not self.samples_ms:
            return f"{self.name}: no samples"
        xs = self.samples_ms
        p95 = statistics.quantiles(xs, n=20)[18] if len(xs) >= 20 else max(xs)
        return (
            f"{self.name}: n={len(xs)} "
            f"min={min(xs):.1f}ms p50={statistics.median(xs):.1f}ms "
            f"p95={p95:.1f}ms max={max(xs):.1f}ms mean={statistics.mean(xs):.1f}ms"
        )


async def _db_banner() -> list[str]:
    from sqlalchemy import text
    from audit_workbench.infra.db.base import async_session_factory
    from audit_workbench.settings import get_settings

    settings = get_settings()
    lines = [f"database_url={settings.database_url}"]
    async with async_session_factory() as session:
        row = (
            await session.execute(
                text("select current_database(), inet_server_addr()::text, inet_server_port()")
            )
        ).one()
        lines.append(f"connected={row[0]} server={row[1]}:{row[2]}")
        counts = (
            await session.execute(text("select status, count(*)::int from runs group by 1 order by 1"))
        ).all()
        lines.append(f"runs_by_status={dict(counts)}")
        idx = (
            await session.execute(
                text(
                    "select indexname from pg_indexes "
                    "where tablename='runs' and indexname like 'ix_runs%' order by 1"
                )
            )
        ).scalars().all()
        lines.append(f"runs_indexes={list(idx)}")
    return lines


async def seed_queued_runs(n: int) -> list[str]:
    """Insert synthetic queued rows for EXPLAIN / position / admission load tests."""
    from sqlalchemy import text
    from audit_workbench.infra.db.base import async_session_factory

    if n <= 0:
        return ["seed_queue: skipped"]
    stamp = uuid.uuid4().hex[:8]
    ids: list[str] = []
    async with async_session_factory() as session:
        wf = (
            await session.execute(text("select id from workflows order by created_at limit 1"))
        ).scalar()
        if not wf:
            return ["seed_queue: no workflow — skip"]
        now = datetime.now(UTC)
        for i in range(n):
            rid = f"AUD-PROF-{stamp}-{i:04d}"
            ids.append(rid)
            await session.execute(
                text(
                    """
                    insert into runs (
                      id, workflow_id, source, status, worker_pool,
                      summary_total, summary_passed, summary_failed, fields_extracted,
                      created_at, progress
                    ) values (
                      :id, :wf, 'profile', 'queued', 'fast',
                      0, 0, 0, 0,
                      :now, CAST(:progress AS json)
                    )
                    on conflict (id) do nothing
                    """
                ),
                {"id": rid, "wf": wf, "now": now, "progress": "{}"},
            )
        await session.commit()
    # Help planner prefer composite queue indexes after bulk insert.
    async with async_session_factory() as session:
        await session.execute(text("ANALYZE runs"))
        await session.commit()
    return [f"seed_queue: inserted {len(ids)} queued runs (prefix AUD-PROF-{stamp})"]


async def cleanup_seeded_runs() -> list[str]:
    from sqlalchemy import text
    from audit_workbench.infra.db.base import async_session_factory

    async with async_session_factory() as session:
        result = await session.execute(
            text("delete from runs where id like 'AUD-PROF-%' and status = 'queued'")
        )
        await session.commit()
        return [f"cleanup: deleted {result.rowcount} AUD-PROF queued rows"]


async def profile_queue_sql(n: int = 50) -> list[str]:
    from sqlalchemy import text
    from audit_workbench.infra.db.base import async_session_factory
    from audit_workbench.app.admission import (
        check_admission,
        count_extract_inflight,
        count_inflight,
        count_queued,
    )
    from audit_workbench.app.queue.position import queue_position

    lines: list[str] = []
    q_count = Sample("count_queued")
    q_pos = Sample("queue_position")
    admit = Sample("check_admission")
    extract = Sample("count_extract_inflight")
    inflight = Sample("count_inflight")

    async with async_session_factory() as session:
        await count_queued(session)
        probe_id = (
            await session.execute(
                text("select id from runs where status='queued' order by created_at desc limit 1")
            )
        ).scalar()

        for _ in range(n):
            t0 = time.perf_counter()
            await count_queued(session)
            q_count.add((time.perf_counter() - t0) * 1000)

            t0 = time.perf_counter()
            await count_inflight(session)
            inflight.add((time.perf_counter() - t0) * 1000)

            t0 = time.perf_counter()
            await count_extract_inflight(session)
            extract.add((time.perf_counter() - t0) * 1000)

            t0 = time.perf_counter()
            await check_admission(session, predicted_pool="extract")
            admit.add((time.perf_counter() - t0) * 1000)

            if probe_id:
                t0 = time.perf_counter()
                await queue_position(session, probe_id)
                q_pos.add((time.perf_counter() - t0) * 1000)

        for label, sql in (
            (
                "count queued",
                "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) SELECT count(*) FROM runs WHERE status = 'queued'",
            ),
            (
                "queue ahead",
                "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) "
                "SELECT count(*) FROM runs WHERE status = 'queued' "
                "AND (created_at < now() OR (created_at = now() AND id < 'AUD-PROF-zzzz'))",
            ),
            (
                "extract inflight",
                "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) SELECT count(*) FROM runs "
                "WHERE status IN ('queued','running') AND worker_pool = 'extract'",
            ),
            (
                "status+pool",
                "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) SELECT count(*) FROM runs "
                "WHERE status = 'queued' AND worker_pool = 'fast'",
            ),
        ):
            plan = (await session.execute(text(sql))).scalars().all()
            lines.append(f"EXPLAIN {label}:")
            lines.extend(f"  {row}" for row in plan)

    lines.append(q_count.report())
    lines.append(inflight.report())
    lines.append(extract.report())
    lines.append(admit.report())
    lines.append(q_pos.report() if q_pos.samples_ms else "queue_position: skipped (no queued run)")
    return lines


async def profile_admission_reject() -> list[str]:
    """Temporarily lower caps and verify CAPACITY path latency."""
    from audit_workbench.infra.db.base import async_session_factory
    from audit_workbench.app.admission import check_admission
    from audit_workbench.settings import get_settings

    settings = get_settings()
    original = (
        settings.admission_max_queued,
        settings.admission_max_inflight,
        settings.admission_max_extract_inflight,
    )
    lines: list[str] = []
    sample = Sample("check_admission_reject")
    try:
        settings.admission_max_queued = 1
        settings.admission_max_inflight = 1
        settings.admission_max_extract_inflight = 1
        async with async_session_factory() as session:
            for _ in range(20):
                t0 = time.perf_counter()
                result = await check_admission(session, predicted_pool="extract")
                sample.add((time.perf_counter() - t0) * 1000)
                if _ == 0:
                    lines.append(
                        f"admission_reject_sample: ok={result.is_ok} "
                        f"code={None if result.is_ok else result.error.code}"
                    )
    finally:
        (
            settings.admission_max_queued,
            settings.admission_max_inflight,
            settings.admission_max_extract_inflight,
        ) = original
    lines.append(sample.report())
    lines.append(
        f"admission_caps_restored queued={original[0]} inflight={original[1]} extract={original[2]}"
    )
    return lines


async def profile_outbox_claim(n: int = 30) -> list[str]:
    from sqlalchemy import text
    from audit_workbench.infra.db.base import async_session_factory

    sample = Sample("outbox_pending_count")
    lines: list[str] = []
    async with async_session_factory() as session:
        exists = (
            await session.execute(
                text("select to_regclass('public.run_dispatch_outbox') is not null")
            )
        ).scalar()
        if not exists:
            return ["outbox: run_dispatch_outbox missing"]
        for _ in range(n):
            t0 = time.perf_counter()
            await session.execute(
                text(
                    "select count(*) from run_dispatch_outbox "
                    "where status in ('pending','dispatching','failed')"
                )
            )
            sample.add((time.perf_counter() - t0) * 1000)
        # EXPLAIN without FOR UPDATE — analyze + row locks are awkward outside a drain.
        plan = (
            await session.execute(
                text(
                    "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) "
                    "SELECT run_id FROM run_dispatch_outbox "
                    "WHERE status = 'pending' "
                    "ORDER BY created_at ASC LIMIT 32"
                )
            )
        ).scalars().all()
        lines.append("EXPLAIN outbox pending poll:")
        lines.extend(f"  {row}" for row in plan)
        counts = (
            await session.execute(
                text("select status, count(*)::int from run_dispatch_outbox group by 1")
            )
        ).all()
        lines.append(f"outbox_by_status={dict(counts)}")
    lines.append(sample.report())
    return lines


async def profile_live_enqueue(base: str, n: int = 20, *, auth: bool) -> list[str]:
    lines: list[str] = []
    enqueue = Sample("POST /v1/workflows/{id}/runs/json")
    health = Sample("GET /v1/healthz")
    headers: dict[str, str] = {}
    if auth:
        from audit_workbench.integration.live_stack import live_auth_headers

        headers = live_auth_headers()
        lines.append(f"live_auth: bearer={'yes' if headers else 'no'}")

    async with httpx.AsyncClient(base_url=base, timeout=30.0, headers=headers) as client:
        hz = await client.get("/v1/healthz")
        if hz.status_code != 200:
            return [f"live healthz failed: {hz.status_code} {hz.text[:200]}"]
        body = hz.json()
        lines.append(
            f"healthz queued={body.get('queuedRuns')} running={body.get('runningRuns')} "
            f"dbPool={body.get('dbPoolSize')} oidc={body.get('oidcEnabled')}"
        )
        wfs = await client.get("/v1/workflows")
        if wfs.status_code != 200:
            return lines + [f"workflows failed: {wfs.status_code} {wfs.text[:160]}"]
        workflows = wfs.json().get("workflows") or []
        if not workflows:
            return lines + ["no workflows for live enqueue profile"]
        wf_id = workflows[0]["id"]

        statuses: dict[int, int] = {}
        for _ in range(n):
            t0 = time.perf_counter()
            await client.get("/v1/healthz")
            health.add((time.perf_counter() - t0) * 1000)

            t0 = time.perf_counter()
            res = await client.post(
                f"/v1/workflows/{wf_id}/runs/json",
                json={
                    "snapshot": {
                        "documents": [],
                        "rules": [],
                        "workflowName": "scale-profile",
                    }
                },
            )
            enqueue.add((time.perf_counter() - t0) * 1000)
            statuses[res.status_code] = statuses.get(res.status_code, 0) + 1
            if res.status_code not in (202, 429, 503):
                lines.append(f"unexpected enqueue status {res.status_code}: {res.text[:160]}")

        lines.append(f"enqueue_status_histogram={statuses}")
    lines.append(health.report())
    lines.append(enqueue.report())
    return lines


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Also hit running API")
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("-n", type=int, default=40)
    parser.add_argument("--seed-queue", type=int, default=0, help="Synthetic queued rows before SQL profile")
    parser.add_argument("--keep-seed", action="store_true", help="Do not delete AUD-PROF rows")
    parser.add_argument("--no-auth", action="store_true", help="Skip Keycloak on live path")
    args = parser.parse_args()

    print("=== Platform scale profile ===")
    for line in await _db_banner():
        print(line)
    for line in await seed_queued_runs(args.seed_queue):
        print(line)
    try:
        print("--- queue SQL ---")
        for line in await profile_queue_sql(n=args.n):
            print(line)
        print("--- admission reject ---")
        for line in await profile_admission_reject():
            print(line)
        print("--- outbox ---")
        for line in await profile_outbox_claim():
            print(line)
        if args.live:
            print("--- live ---")
            for line in await profile_live_enqueue(
                args.base, n=min(args.n, 25), auth=not args.no_auth
            ):
                print(line)
    finally:
        if args.seed_queue and not args.keep_seed:
            for line in await cleanup_seeded_runs():
                print(line)
    print("=== done ===")


if __name__ == "__main__":
    asyncio.run(main())
