"""Production-scale platform stress test — real extraction queue at 1000+ documents.

Run inside the API pod (see scripts/prod-stress.mjs) or locally against a live API:

  python backend/scripts/prod_stress_test.py --api http://127.0.0.1:8000 --count 1000
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import random
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx

_BACKEND = Path(__file__).resolve().parents[1]
for _path in (_BACKEND / "src", _BACKEND):
    _text = str(_path)
    if _text not in sys.path:
        sys.path.insert(0, _text)

from scripts.benchmark_dev_stress import (  # noqa: E402
    RunLifecycle,
    StressReport,
    _build_summary,
    _jitter,
    _record,
    _retry_after_s,
    _save_workflow,
    _start_valid_run,
    _track_run,
    _wait_drain,
    phase_invalid_files,
)
from scripts.benchmark_ui_route import DEFAULT_PDF  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STRESS_PDF = Path("/tmp/Facture.pdf")


def _default_output_path() -> Path:
    preferred = REPO_ROOT / "benchmark-reports" / "prod-stress.json"
    try:
        preferred.parent.mkdir(parents=True, exist_ok=True)
        return preferred
    except OSError:
        return Path("/tmp/prod-stress.json")

_MAX_ENQUEUE_RETRIES = 12
_TRACKER_SAMPLE_SIZE = 40
_IN_CLUSTER_TOKEN_URL = os.environ.get(
    "STRESS_OIDC_TOKEN_URL",
    "http://keycloak:8080/realms/repody/protocol/openid-connect/token",
)
_IN_CLUSTER_CLIENT_ID = os.environ.get("STRESS_OIDC_CLIENT_ID", "repody-web")
_IN_CLUSTER_CLIENT_SECRET = os.environ.get("STRESS_OIDC_CLIENT_SECRET", "repody-web-dev-secret")
_IN_CLUSTER_USERNAME = os.environ.get("STRESS_OIDC_USERNAME", "operator@repody.local")
_IN_CLUSTER_PASSWORD = os.environ.get("STRESS_OIDC_PASSWORD", "repody-dev")


def _fetch_in_cluster_token() -> str:
    from audit_workbench.auth.keycloak_token import fetch_password_grant_token_sync

    return fetch_password_grant_token_sync(
        token_url=_IN_CLUSTER_TOKEN_URL,
        client_id=_IN_CLUSTER_CLIENT_ID,
        client_secret=_IN_CLUSTER_CLIENT_SECRET,
        username=_IN_CLUSTER_USERNAME,
        password=_IN_CLUSTER_PASSWORD,
        timeout=30.0,
    )


def _apply_bearer(client: httpx.AsyncClient, args: argparse.Namespace) -> None:
    if args.in_cluster_auth:
        args.bearer_token = _fetch_in_cluster_token()
    if args.bearer_token:
        client.headers["Authorization"] = f"Bearer {args.bearer_token}"


def _rewrite_upload_url(upload_url: str, base: str) -> tuple[str, str | None]:
    parsed = urlparse(upload_url)
    base_parsed = urlparse(base.rstrip("/"))
    rewritten = urlunparse(
        parsed._replace(
            scheme=base_parsed.scheme or parsed.scheme,
            netloc=base_parsed.netloc or parsed.netloc,
        )
    )
    signed_host = parsed.netloc or None
    return rewritten, signed_host


async def _upload_presign_cluster(
    client: httpx.AsyncClient,
    *,
    doc_id: str,
    filename: str,
    data: bytes,
    mime: str,
    minio_upload_base: str | None,
) -> dict[str, str]:
    presign_res = await client.post(
        "/v1/uploads/presign",
        json={
            "files": [
                {
                    "fileName": filename,
                    "mimeType": mime,
                    "size": len(data),
                    "documentId": doc_id,
                }
            ]
        },
    )
    presign_res.raise_for_status()
    payload = presign_res.json()
    if payload.get("uploadMode") != "presigned":
        raise RuntimeError("presign_unavailable")
    item = payload["uploads"][0]
    upload_url = item.get("uploadUrl")
    if not upload_url:
        raise RuntimeError("Missing presign upload URL")

    signed_host: str | None = None
    if minio_upload_base:
        upload_url, signed_host = _rewrite_upload_url(upload_url, minio_upload_base)

    headers = dict(item.get("headers") or {"Content-Type": mime})
    if signed_host:
        headers["Host"] = signed_host

    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as put_client:
        put_res = await put_client.put(
            upload_url,
            content=data,
            headers=headers,
        )
        put_res.raise_for_status()

    confirm_res = await client.post(
        "/v1/uploads/confirm",
        json={"storageKeys": [item["storageKey"]]},
    )
    confirm_res.raise_for_status()
    return {
        "documentId": doc_id,
        "storageKey": item["storageKey"],
        "mimeType": mime,
        "fileName": filename,
    }


@dataclass
class QueueObservation:
    run_id: str
    t_ms: int
    position: int
    depth: int


@dataclass
class ProdStressReport(StressReport):
    preflight: dict[str, Any] = field(default_factory=dict)
    enqueue_rejections: list[dict[str, Any]] = field(default_factory=list)
    queue_observations: list[QueueObservation] = field(default_factory=list)
    slo: dict[str, Any] = field(default_factory=dict)


async def _readiness(client: httpx.AsyncClient, report: ProdStressReport, t0: float) -> dict[str, Any]:
    start = time.perf_counter()
    res = await client.get("/v1/healthz")
    latency = (time.perf_counter() - start) * 1000
    await _record(
        report,
        phase="readiness",
        method="GET",
        path="/v1/healthz",
        status=res.status_code,
        latency_ms=latency,
    )
    body = res.json() if res.content else {}
    if not isinstance(body, dict):
        body = {}
    if not res.is_success and not body:
        return {}
    report.health_samples.append(
        {
            "t_ms": round((time.perf_counter() - t0) * 1000),
            "queuedRuns": body.get("queuedRuns"),
            "runningRuns": body.get("runningRuns"),
            "inflightRuns": body.get("inflightRuns"),
        }
    )
    return body


async def preflight(
    client: httpx.AsyncClient,
    report: ProdStressReport,
    *,
    t0: float,
    require_workers: bool,
    min_admission_queued: int,
) -> dict[str, Any]:
    body = await _readiness(client, report, t0)
    worker_pools = body.get("workerPools") or {}
    extract_pool = str(worker_pools.get("extract") or "")
    fast_pool = str(worker_pools.get("fast") or "")

    checks: list[dict[str, Any]] = []

    def _check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "pass": ok, "detail": detail})
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {name}: {detail}")

    _check("healthz", body.get("status") in ("ok", "degraded"), f"status={body.get('status')}")
    _check("redis", bool(body.get("redisOk")), f"redisOk={body.get('redisOk')}")
    _check("taskiq", bool(body.get("taskiqConfigured")), "Taskiq broker configured")
    _check(
        "worker_pools",
        bool(extract_pool) and bool(fast_pool),
        f"fast={fast_pool!r} extract={extract_pool!r}",
    )

    mode = str(body.get("inference") or "").lower()
    vllm_ok = body.get("vllm")
    if mode == "vllm" and require_workers:
        _check(
            "vllm_reachable",
            vllm_ok is True or vllm_ok is None,
            f"vllm={vllm_ok} (set AUDIT_HEALTHZ_PROBE_INFERENCE=true to probe GPU)",
        )
    else:
        _check("inference", bool(mode), f"inference={body.get('inference')}")

    admission_on = bool(body.get("admissionControlEnabled"))
    _check("admission_enabled", admission_on, f"admissionControlEnabled={admission_on}")

    max_queued = body.get("admissionMaxQueued")
    max_extract = body.get("admissionMaxExtractInflight")
    if admission_on and max_queued is not None:
        headroom_ok = int(max_queued) >= min_admission_queued
        _check(
            "admission_headroom",
            headroom_ok,
            f"admissionMaxQueued={max_queued} need>={min_admission_queued}",
        )
    else:
        _check(
            "admission_headroom",
            True,
            f"admission limits not on healthz — merge deploy/client/lab/values.stress-test.crc.yaml",
        )

    if admission_on and max_extract is not None:
        _check(
            "extract_inflight_cap",
            int(max_extract) >= 1,
            f"admissionMaxExtractInflight={max_extract} (align with VLM parallel slots)",
        )

    snapshot = {
        "checks": checks,
        "workerPools": worker_pools,
        "queuedRuns": body.get("queuedRuns"),
        "runningRuns": body.get("runningRuns"),
        "rateLimitEnabled": body.get("rateLimitEnabled"),
        "admissionControlEnabled": admission_on,
        "admissionMaxQueued": max_queued,
        "admissionMaxInflight": body.get("admissionMaxInflight"),
        "admissionMaxExtractInflight": max_extract,
    }
    report.preflight = snapshot

    if any(
        not c["pass"]
        for c in checks
        if c["name"] in ("healthz", "redis", "taskiq", "admission_headroom")
    ):
        raise RuntimeError("Preflight failed — fix platform health before stress test")
    if require_workers and mode == "vllm" and vllm_ok is False:
        raise RuntimeError("VLM inference is not reachable — fix AUDIT_VLLM_BASE_URL before stress test")
    return snapshot


async def _enqueue_with_retry(
    client: httpx.AsyncClient,
    report: ProdStressReport,
    *,
    workflow_id: str,
    doc_id: str,
    binding: dict[str, str],
    index: int,
    sem: asyncio.Semaphore,
    args: argparse.Namespace,
) -> RunLifecycle | None:
    probe = f"prod_{index}_{uuid.uuid4().hex[:8]}"
    async with sem:
        for attempt in range(_MAX_ENQUEUE_RETRIES):
            try:
                run_id, enqueue_ms = await _start_valid_run(
                    client,
                    workflow_id=workflow_id,
                    doc_id=doc_id,
                    binding=binding,
                    probe=probe,
                )
                return RunLifecycle(
                    run_id=run_id,
                    enqueued_ms=round((time.perf_counter() - report._t0) * 1000),  # type: ignore[attr-defined]
                    enqueue_latency_ms=enqueue_ms,
                )
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                detail = exc.response.text[:300]
                await _record(
                    report,
                    phase="enqueue",
                    method="POST",
                    path=f"/v1/workflows/{workflow_id}/runs/json",
                    status=status,
                    latency_ms=0,
                    detail=f"attempt={attempt + 1} {detail}",
                )
                if status == 401 and args.in_cluster_auth:
                    _apply_bearer(client, args)
                    await asyncio.sleep(_jitter(0.5))
                    continue
                if status not in (429, 503):
                    report.enqueue_rejections.append(
                        {"index": index, "status": status, "detail": detail, "attempt": attempt + 1}
                    )
                    return None
                retry_s = _retry_after_s(exc.response) or min(60.0, 2.0 ** attempt)
                await asyncio.sleep(_jitter(retry_s))
        report.enqueue_rejections.append(
            {"index": index, "status": "exhausted", "detail": "max enqueue retries", "attempt": _MAX_ENQUEUE_RETRIES}
        )
        return None


async def _queue_position_sampler(
    client: httpx.AsyncClient,
    report: ProdStressReport,
    run_ids: list[str],
    *,
    t0: float,
    stop: asyncio.Event,
    interval_s: float,
) -> None:
    if not run_ids:
        return
    sample = run_ids[: min(len(run_ids), _TRACKER_SAMPLE_SIZE)]
    wait_s = interval_s
    while not stop.is_set():
        for run_id in sample:
            if stop.is_set():
                break
            try:
                res = await client.get(f"/v1/runs/{run_id}/status")
                if res.status_code == 429:
                    retry_s = _retry_after_s(res) or 4.0
                    await asyncio.sleep(_jitter(retry_s))
                    continue
                if not res.is_success:
                    continue
                body = res.json()
                if str(body.get("status") or "") != "queued":
                    continue
                progress = body.get("progress") or {}
                pos = progress.get("queuePosition")
                depth = progress.get("queueDepth")
                if pos is None or depth is None:
                    continue
                report.queue_observations.append(
                    QueueObservation(
                        run_id=run_id,
                        t_ms=round((time.perf_counter() - t0) * 1000),
                        position=int(pos),
                        depth=int(depth),
                    )
                )
            except httpx.HTTPError:
                pass
        await asyncio.sleep(_jitter(wait_s))


async def _finalize_pending(
    client: httpx.AsyncClient,
    lifecycles: list[RunLifecycle],
    *,
    t0: float,
    stop: asyncio.Event,
    poll_s: float,
    concurrency: int,
    args: argparse.Namespace,
) -> None:
    pending = [lc for lc in lifecycles if lc.terminal_status is None]
    if not pending:
        return
    sem = asyncio.Semaphore(concurrency)
    finalize_deadline_s = max(120.0, len(pending) * 10.0)

    async def _poll_one(lc: RunLifecycle) -> None:
        async with sem:
            deadline = time.perf_counter() + finalize_deadline_s
            while lc.terminal_status is None and time.perf_counter() < deadline and not stop.is_set():
                try:
                    res = await client.get(f"/v1/runs/{lc.run_id}/status")
                    if res.status_code == 401 and args.in_cluster_auth:
                        _apply_bearer(client, args)
                        await asyncio.sleep(_jitter(poll_s))
                        continue
                    if not res.is_success:
                        await asyncio.sleep(_jitter(poll_s))
                        continue
                    body = res.json()
                    status = str(body.get("status") or "")
                    progress = body.get("progress") or {}
                    pos = progress.get("queuePosition")
                    depth = progress.get("queueDepth")
                    if pos is not None:
                        lc.max_queue_position = max(lc.max_queue_position or 0, int(pos))
                    if depth is not None:
                        lc.max_queue_depth = max(lc.max_queue_depth or 0, int(depth))
                    now_ms = round((time.perf_counter() - t0) * 1000)
                    if status == "running" and lc.first_running_ms is None:
                        lc.first_running_ms = now_ms - lc.enqueued_ms
                    if status in ("done", "failed"):
                        lc.terminal_ms = now_ms - lc.enqueued_ms
                        lc.terminal_status = status
                        if status == "failed":
                            lc.error = str(body.get("error") or "")[:500]
                        return
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(_jitter(poll_s))

    await asyncio.gather(*[_poll_one(lc) for lc in pending])


def _queue_position_updates_valid(observations: list[QueueObservation]) -> dict[str, Any]:
    by_run: dict[str, list[QueueObservation]] = {}
    for obs in observations:
        by_run.setdefault(obs.run_id, []).append(obs)

    runs_with_updates = 0
    monotonic_decrease = 0
    for samples in by_run.values():
        if len(samples) < 2:
            continue
        ordered = sorted(samples, key=lambda o: o.t_ms)
        runs_with_updates += 1
        positions = [s.position for s in ordered]
        if all(positions[i] >= positions[i + 1] for i in range(len(positions) - 1)):
            monotonic_decrease += 1

    return {
        "sampledRuns": len(by_run),
        "runsWithMultipleSamples": runs_with_updates,
        "runsWithMonotonicPositionDecrease": monotonic_decrease,
        "totalObservations": len(observations),
    }


def _evaluate_slo(report: ProdStressReport, *, strict: bool, target_count: int) -> dict[str, Any]:
    summary = report.summary
    submitted = int(summary.get("runsSubmitted") or 0)
    done = int(summary.get("runsDone") or 0)
    failed = int(summary.get("runsFailed") or 0)
    pending = int(summary.get("runsPending") or 0)
    invalid_pass = str(summary.get("invalidFilesPass") or "")
    invalid_ok = invalid_pass.endswith(f"/{len(report.invalid_file_results)}") and invalid_pass.startswith(
        f"{len(report.invalid_file_results)}/"
    )

    success_rate = (done / submitted) if submitted else 0.0
    queue_meta = _queue_position_updates_valid(report.queue_observations)

    gates: list[dict[str, Any]] = [
        {
            "name": "enqueue_target",
            "pass": submitted >= target_count,
            "detail": f"submitted={submitted} target={target_count}",
        },
        {
            "name": "drain_complete",
            "pass": pending == 0,
            "detail": f"pending={pending}",
        },
        {
            "name": "success_rate",
            "pass": success_rate >= (0.99 if strict else 0.95),
            "detail": f"done={done} failed={failed} rate={success_rate:.3f}",
        },
        {
            "name": "invalid_file_guards",
            "pass": invalid_ok or len(report.invalid_file_results) == 0,
            "detail": invalid_pass,
        },
        {
            "name": "queue_depth_observed",
            "pass": int(summary.get("maxObservedQueueDepth") or 0) >= min(2, target_count)
            or int(summary.get("healthMaxQueued") or 0) >= 1,
            "detail": f"maxDepth={summary.get('maxObservedQueueDepth')} healthMaxQueued={summary.get('healthMaxQueued')}",
        },
        {
            "name": "queue_position_updates",
            "pass": queue_meta["runsWithMultipleSamples"] >= 1
            or target_count <= 1
            or (not strict and target_count <= 20 and done == submitted and submitted > 0),
            "detail": str(queue_meta),
        },
    ]

    passed = all(g["pass"] for g in gates)
    return {"pass": passed, "strict": strict, "gates": gates, "queuePositionAudit": queue_meta}


async def run_prod_stress(args: argparse.Namespace) -> int:
    pdf_path = args.document
    if not pdf_path.is_file():
        print(f"Missing document: {pdf_path}", file=sys.stderr)
        return 2

    pdf_bytes = pdf_path.read_bytes()
    timeout = httpx.Timeout(180.0, connect=20.0)
    workflow_id = f"wf-prod-stress-{uuid.uuid4().hex[:8]}"
    doc_id = f"doc-{uuid.uuid4().hex[:6]}"
    report = ProdStressReport(
        started_at=datetime.now(UTC).isoformat(),
        api=args.api.rstrip("/"),
        config=vars(args),
    )
    stop = asyncio.Event()
    wall_start = time.perf_counter()
    report._t0 = wall_start  # type: ignore[attr-defined]
    t0 = wall_start

    async with httpx.AsyncClient(
        base_url=args.api.rstrip("/"),
        timeout=timeout,
    ) as client:
        _apply_bearer(client, args)
        print("Phase 0: preflight …")
        await preflight(
            client,
            report,
            t0=t0,
            require_workers=args.require_workers,
            min_admission_queued=args.count,
        )

        await _save_workflow(client, workflow_id, doc_id)
        binding = await _upload_presign_cluster(
            client,
            doc_id=doc_id,
            filename=pdf_path.name,
            data=pdf_bytes,
            mime="application/pdf",
            minio_upload_base=args.minio_upload_base,
        )

        if not args.skip_invalid:
            print("Phase 1: invalid / unsupported file guards …")
            await phase_invalid_files(client, report, workflow_id=workflow_id, doc_id=doc_id, pdf_bytes=pdf_bytes)

        print(f"Phase 2: enqueue {args.count} real extraction runs (concurrency={args.concurrency}) …")
        enqueue_sem = asyncio.Semaphore(args.concurrency)
        enqueue_tasks = [
            _enqueue_with_retry(
                client,
                report,
                workflow_id=workflow_id,
                doc_id=doc_id,
                binding=binding,
                index=i,
                sem=enqueue_sem,
                args=args,
            )
            for i in range(args.count)
        ]
        enqueue_results = await asyncio.gather(*enqueue_tasks)
        lifecycles = [lc for lc in enqueue_results if lc is not None]
        report.runs.extend(lifecycles)
        print(f"  Enqueued {len(lifecycles)}/{args.count} runs ({len(report.enqueue_rejections)} hard failures)")

        _apply_bearer(client, args)
        sample_ids = [lc.run_id for lc in lifecycles]
        sample_trackers = [
            asyncio.create_task(
                _track_run(client, lc, t0=t0, stop=stop, poll_s=args.poll_interval_s),
            )
            for lc in lifecycles[: min(len(lifecycles), _TRACKER_SAMPLE_SIZE)]
        ]
        sampler = asyncio.create_task(
            _queue_position_sampler(
                client,
                report,
                sample_ids,
                t0=t0,
                stop=stop,
                interval_s=max(args.poll_interval_s, 2.0),
            )
        )

        print("Phase 3: drain queue (real extraction + validation) …")
        try:
            await _wait_drain(
                client,
                report,
                t0=t0,
                timeout_s=args.timeout_seconds,
                poll_s=max(args.poll_interval_s, 2.0),
            )
        except TimeoutError as exc:
            print(f"  WARNING: {exc}", file=sys.stderr)
        finally:
            stop.set()
            sampler.cancel()
            await asyncio.gather(*sample_trackers, return_exceptions=True)
            with contextlib.suppress(asyncio.CancelledError):
                await sampler

        print("Phase 4: finalize run statuses …")
        _apply_bearer(client, args)
        await _finalize_pending(
            client,
            lifecycles,
            t0=t0,
            stop=stop,
            poll_s=args.poll_interval_s,
            concurrency=min(32, args.concurrency),
            args=args,
        )

        try:
            await client.delete(f"/v1/workflows/{workflow_id}")
        except httpx.HTTPError:
            pass

    wall_ms = (time.perf_counter() - wall_start) * 1000
    report.summary = _build_summary(report, wall_ms=wall_ms)
    report.summary["enqueueRejections"] = len(report.enqueue_rejections)
    report.summary["targetCount"] = args.count
    report.slo = _evaluate_slo(report, strict=args.strict, target_count=args.count)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "startedAt": report.started_at,
        "api": report.api,
        "config": {
            k: "<redacted>" if "token" in k.lower() else str(v) if isinstance(v, Path) else v
            for k, v in report.config.items()
            if not callable(v)
        },
        "preflight": report.preflight,
        "summary": report.summary,
        "slo": report.slo,
        "invalidFileResults": report.invalid_file_results,
        "enqueueRejections": report.enqueue_rejections,
        "queueObservations": [o.__dict__ for o in report.queue_observations],
        "runs": [r.__dict__ for r in report.runs],
        "healthSamples": report.health_samples,
        "httpEventCount": len(report.http_events),
    }
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    s = report.summary
    slo = report.slo
    print("\n=== Production stress test summary ===")
    print(f"  Wall time:           {s['wallMs']} ms")
    print(f"  Target / submitted:  {args.count} / {s['runsSubmitted']}")
    print(f"  Done / failed / pend:{s['runsDone']} / {s['runsFailed']} / {s['runsPending']}")
    print(f"  Throughput:          {s['throughputRunsPerMinute']} runs/min")
    print(f"  Max queue depth:     {s['maxObservedQueueDepth']} (health max={s['healthMaxQueued']})")
    print(f"  Queue wait ms:       {s['queueWaitMs']}")
    print(f"  Total run ms:        {s['totalRunMs']}")
    print(f"  429/503 hits:        {s['rateLimitOrAdmissionHits']}")
    print(f"  Enqueue rejections:  {s.get('enqueueRejections', 0)}")
    print(f"  SLO:                 {'PASS' if slo['pass'] else 'FAIL'}")
    for gate in slo["gates"]:
        mark = "OK" if gate["pass"] else "FAIL"
        print(f"    [{mark}] {gate['name']}: {gate['detail']}")
    print(f"\nReport: {args.output}")

    if args.strict and not slo["pass"]:
        return 1
    if int(s.get("runsPending") or 0) > 0:
        return 1
    if len(lifecycles) < args.count and args.strict:
        return 1
    return 0


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--bearer-token",
        default=None,
        help="OIDC access token for auth-enabled stacks.",
    )
    parser.add_argument(
        "--in-cluster-auth",
        action="store_true",
        help="Fetch/refresh OIDC token from Keycloak inside the API pod (recommended for long runs).",
    )
    parser.add_argument("--document", type=Path, default=DEFAULT_STRESS_PDF if DEFAULT_STRESS_PDF.is_file() else DEFAULT_PDF)
    parser.add_argument("--count", type=int, default=1000, help="Number of real extraction runs to enqueue")
    parser.add_argument("--concurrency", type=int, default=24, help="Max concurrent enqueue requests")
    parser.add_argument("--poll-interval-s", type=float, default=2.0)
    parser.add_argument("--timeout-seconds", type=float, default=14_400.0, help="Max wait for queue drain (default 4h)")
    parser.add_argument("--require-workers", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--minio-upload-base",
        default=None,
        help="Rewrite presigned PUT host (e.g. http://repody-data-minio:9000 for in-cluster runs).",
    )
    parser.add_argument("--skip-invalid", action="store_true", help="Skip invalid-file guard phase")
    parser.add_argument("--strict", action="store_true", help="Fail when SLO gates are not met")
    parser.add_argument(
        "--output",
        type=Path,
        default=_default_output_path(),
    )


async def main() -> int:
    parser = argparse.ArgumentParser(description="Production-scale Repody stress test")
    add_arguments(parser)
    args = parser.parse_args()
    return await run_prod_stress(args)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
