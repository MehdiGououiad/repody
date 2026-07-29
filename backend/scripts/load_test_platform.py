"""Real-world platform load test — control plane + JSON fast path + admission.

Mimics operators and API clients: list workflows/audits, enqueue empty JSON runs,
poll status while queued, saturate admission caps, measure claim→done latency.

Does **not** stress VLM extraction (use ``prod_stress_test.py`` for that).

Usage (stack up: API + Postgres + Redis + workers + Keycloak):

  $env:E2E_STACK='1'
  $env:AUDIT_DATABASE_URL='postgresql+asyncpg://audit:audit-local-dev@127.0.0.1:5432/repody'
  node scripts/backend-run.mjs --dev python scripts/load_test_platform.py
  node scripts/backend-run.mjs --dev python scripts/load_test_platform.py --concurrency 40 --enqueue 200
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Sample:
    name: str
    samples_ms: list[float] = field(default_factory=list)
    statuses: dict[int, int] = field(default_factory=dict)

    def add(self, ms: float, status: int | None = None) -> None:
        self.samples_ms.append(ms)
        if status is not None:
            self.statuses[status] = self.statuses.get(status, 0) + 1

    def report(self) -> str:
        if not self.samples_ms:
            return f"{self.name}: no samples"
        xs = self.samples_ms
        p95 = statistics.quantiles(xs, n=20)[18] if len(xs) >= 20 else max(xs)
        status_bit = f" statuses={dict(sorted(self.statuses.items()))}" if self.statuses else ""
        return (
            f"{self.name}: n={len(xs)} "
            f"min={min(xs):.1f}ms p50={statistics.median(xs):.1f}ms "
            f"p95={p95:.1f}ms max={max(xs):.1f}ms mean={statistics.mean(xs):.1f}ms"
            f"{status_bit}"
        )


def _auth_headers() -> dict[str, str]:
    from repody.integration.live_stack import live_auth_headers, live_oidc_enabled

    if not live_oidc_enabled():
        return {}
    return live_auth_headers()


async def _phase_control_plane(client: httpx.AsyncClient, n: int) -> list[str]:
    health = Sample("GET /v1/healthz")
    workflows = Sample("GET /v1/workflows")
    audits = Sample("GET /v1/audits")
    dashboard = Sample("GET /v1/dashboard")
    lines: list[str] = []

    async def one() -> None:
        t0 = time.perf_counter()
        r = await client.get("/v1/healthz")
        health.add((time.perf_counter() - t0) * 1000, r.status_code)

        t0 = time.perf_counter()
        r = await client.get("/v1/workflows")
        workflows.add((time.perf_counter() - t0) * 1000, r.status_code)

        t0 = time.perf_counter()
        r = await client.get("/v1/audits")
        audits.add((time.perf_counter() - t0) * 1000, r.status_code)

        t0 = time.perf_counter()
        r = await client.get("/v1/dashboard")
        dashboard.add((time.perf_counter() - t0) * 1000, r.status_code)

    await asyncio.gather(*(one() for _ in range(n)))
    hz = await client.get("/v1/healthz")
    body = hz.json() if hz.status_code == 200 else {}
    lines.append(
        f"healthz snapshot queued={body.get('queuedRuns')} running={body.get('runningRuns')} "
        f"dbPool={body.get('dbPoolSize')} redisOk={body.get('redisOk')}"
    )
    lines.extend(
        [health.report(), workflows.report(), audits.report(), dashboard.report()]
    )
    return lines

async def _pick_workflow(client: httpx.AsyncClient) -> str:
    from repody.infra.db.seed import SEED_WORKFLOW_ID

    res = await client.get("/v1/workflows")
    res.raise_for_status()
    workflows = res.json().get("workflows") or []
    ids = {w["id"] for w in workflows}
    if SEED_WORKFLOW_ID in ids:
        return SEED_WORKFLOW_ID
    if not workflows:
        raise RuntimeError("no workflows — seed the DB (wf-invoice-audit)")
    return workflows[0]["id"]


async def _enqueue_one(
    client: httpx.AsyncClient,
    wf_id: str,
    sample: Sample,
) -> str | None:
    t0 = time.perf_counter()
    res = await client.post(
        f"/v1/workflows/{wf_id}/runs/json",
        json={
            "snapshot": {
                "documents": [],
                "rules": [],
                "workflowName": "load-test",
            }
        },
    )
    sample.add((time.perf_counter() - t0) * 1000, res.status_code)
    if res.status_code == 202:
        return res.json().get("runId")
    return None


async def _phase_enqueue_storm(
    client: httpx.AsyncClient,
    wf_id: str,
    *,
    total: int,
    concurrency: int,
) -> tuple[list[str], list[str]]:
    sample = Sample("POST /runs/json enqueue")
    run_ids: list[str] = []
    sem = asyncio.Semaphore(concurrency)

    async def worker() -> None:
        async with sem:
            rid = await _enqueue_one(client, wf_id, sample)
            if rid:
                run_ids.append(rid)

    await asyncio.gather(*(worker() for _ in range(total)))
    return [sample.report(), f"accepted_run_ids={len(run_ids)}"], run_ids


async def _phase_poll_storm(
    client: httpx.AsyncClient,
    run_ids: list[str],
    *,
    rounds: int,
    concurrency: int,
) -> list[str]:
    if not run_ids:
        return ["poll storm: skipped (no accepted runs)"]
    sample = Sample("GET /runs/{id}/status poll")
    targets = run_ids[: min(40, len(run_ids))]
    sem = asyncio.Semaphore(concurrency)

    async def poll_one(run_id: str) -> None:
        async with sem:
            t0 = time.perf_counter()
            res = await client.get(f"/v1/runs/{run_id}/status")
            sample.add((time.perf_counter() - t0) * 1000, res.status_code)

    for _ in range(rounds):
        await asyncio.gather(*(poll_one(rid) for rid in targets))
    return [sample.report()]


async def _phase_wait_completions(
    client: httpx.AsyncClient,
    run_ids: list[str],
    *,
    timeout_s: float,
    sample_n: int,
) -> list[str]:
    if not run_ids:
        return ["completion: skipped"]
    sample = Sample("enqueue-to-terminal (sampled)")
    targets = run_ids[:sample_n]
    deadline = time.monotonic() + timeout_s
    pending = set(targets)
    started = {rid: time.perf_counter() for rid in targets}
    done_ok = 0
    failed = 0

    while pending and time.monotonic() < deadline:
        still: set[str] = set()
        for rid in list(pending):
            res = await client.get(f"/v1/runs/{rid}/status")
            if res.status_code != 200:
                still.add(rid)
                continue
            status = res.json().get("status")
            if status in ("done", "failed"):
                sample.add((time.perf_counter() - started[rid]) * 1000)
                if status == "done":
                    done_ok += 1
                else:
                    failed += 1
            else:
                still.add(rid)
        pending = still
        if pending:
            await asyncio.sleep(0.25)

    return [
        sample.report(),
        f"completion sampled done={done_ok} failed={failed} timed_out={len(pending)}",
    ]


async def _phase_admission_saturate(
    client: httpx.AsyncClient,
    wf_id: str,
    *,
    burst: int,
    concurrency: int,
) -> list[str]:
    """Push enqueue until 503 CAPACITY appears (or burst exhausted)."""
    sample = Sample("admission saturate enqueue")
    sem = asyncio.Semaphore(concurrency)

    async def worker() -> None:
        async with sem:
            await _enqueue_one(client, wf_id, sample)

    await asyncio.gather(*(worker() for _ in range(burst)))
    lines = [sample.report()]
    if 503 not in sample.statuses:
        lines.append(
            "admission note: no 503 in burst — raise --admission-burst or lower "
            "AUDIT_ADMISSION_MAX_QUEUED for this phase"
        )
    else:
        lines.append("admission: CAPACITY (503) observed under load")
    return lines


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--concurrency", type=int, default=32)
    parser.add_argument("--control-plane", type=int, default=40, help="Control-plane iterations")
    parser.add_argument("--enqueue", type=int, default=120, help="JSON enqueue storm size")
    parser.add_argument("--poll-rounds", type=int, default=8)
    parser.add_argument("--completion-timeout", type=float, default=90.0)
    parser.add_argument("--admission-burst", type=int, default=80)
    parser.add_argument(
        "--skip-admission",
        action="store_true",
        help="Skip admission saturation (avoids filling the queue)",
    )
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    headers = _auth_headers()
    report: list[str] = ["=== Platform load test (real-world mix) ==="]

    async with httpx.AsyncClient(
        base_url=args.base.rstrip("/"),
        headers=headers,
        timeout=httpx.Timeout(60.0),
    ) as client:
        hz = await client.get("/v1/healthz")
        if hz.status_code != 200:
            raise SystemExit(f"API not ready: {hz.status_code} {hz.text[:200]}")
        report.append(f"auth={'bearer' if headers else 'none'}")
        report.append(f"healthz={json.dumps(hz.json(), sort_keys=True)[:240]}")

        report.append("--- control plane ---")
        report.extend(await _phase_control_plane(client, args.control_plane))

        wf_id = await _pick_workflow(client)
        report.append(f"workflow_id={wf_id}")

        report.append("--- enqueue storm (JSON fast path) ---")
        lines, run_ids = await _phase_enqueue_storm(
            client, wf_id, total=args.enqueue, concurrency=args.concurrency
        )
        report.extend(lines)

        report.append("--- poll storm ---")
        report.extend(
            await _phase_poll_storm(
                client,
                run_ids,
                rounds=args.poll_rounds,
                concurrency=args.concurrency,
            )
        )

        report.append("--- completion sample ---")
        report.extend(
            await _phase_wait_completions(
                client,
                run_ids,
                timeout_s=args.completion_timeout,
                sample_n=min(40, len(run_ids)),
            )
        )

        if not args.skip_admission:
            report.append("--- admission saturate ---")
            report.append(
                "note: rate limits may return 429 before CAPACITY 503; "
                "flush LIMITS* Redis keys or set AUDIT_RATE_LIMIT_ENABLED=false to isolate admission"
            )
            report.extend(
                await _phase_admission_saturate(
                    client,
                    wf_id,
                    burst=args.admission_burst,
                    concurrency=args.concurrency,
                )
            )

        hz2 = await client.get("/v1/healthz")
        if hz2.status_code == 200:
            body = hz2.json()
            report.append(
                f"post healthz queued={body.get('queuedRuns')} running={body.get('runningRuns')} "
                f"inflight={body.get('inflightRuns')}"
            )

    report.append("=== done ===")
    text = "\n".join(report)
    print(text)
    out = args.out or (REPO_ROOT / "benchmark-reports" / "platform-load.json")
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps({"lines": report, "ts": time.time()}, indent=2),
            encoding="utf-8",
        )
        print(f"wrote {out}")
    except OSError as exc:
        print(f"report write skipped: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
