"""Platform stress test — use via benchmark_dev.py stress."""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import httpx

_BACKEND = Path(__file__).resolve().parents[1]
for _path in (_BACKEND / "src", _BACKEND):
    _text = str(_path)
    if _text not in sys.path:
        sys.path.insert(0, _text)

from audit_workbench.extraction.document_model_branding import REPODY_VLM_CATALOG_ID  # noqa: E402
from scripts.benchmark_ui_route import DEFAULT_PDF, _upload_presign  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]

# Minimal valid PDF (one empty page) for synthetic uploads when needed.
_MINIMAL_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
    b"0000000052 00000 n \n0000000101 00000 n \n"
    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n149\n%%EOF\n"
)
_MAX_POLL_S = 10.0
_QUEUED_POLL_S = 4.0
_RATE_LIMIT_POLL_S = 4.0


def _retry_after_s(response: httpx.Response) -> float | None:
    raw = response.headers.get("retry-after")
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        pass
    try:
        retry_at = parsedate_to_datetime(raw)
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)
        return max(0.0, retry_at.timestamp() - datetime.now(UTC).timestamp())
    except (TypeError, ValueError):
        return None


def _jitter(wait_s: float) -> float:
    return wait_s * random.uniform(0.85, 1.15)


@dataclass
class HttpEvent:
    phase: str
    method: str
    path: str
    status: int
    latency_ms: float
    detail: str = ""


@dataclass
class RunLifecycle:
    run_id: str
    enqueued_ms: int
    enqueue_latency_ms: float
    first_running_ms: int | None = None
    terminal_ms: int | None = None
    terminal_status: str | None = None
    max_queue_position: int | None = None
    max_queue_depth: int | None = None
    error: str | None = None


@dataclass
class StressReport:
    started_at: str
    api: str
    config: dict[str, Any]
    invalid_file_results: list[dict[str, Any]] = field(default_factory=list)
    http_events: list[HttpEvent] = field(default_factory=list)
    runs: list[RunLifecycle] = field(default_factory=list)
    health_samples: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


def _percentiles(values: list[float], ps: tuple[int, ...] = (50, 95, 99)) -> dict[str, float]:
    if not values:
        return {}
    ordered = sorted(values)
    out: dict[str, float] = {}
    for p in ps:
        idx = max(0, min(len(ordered) - 1, round((p / 100) * (len(ordered) - 1))))
        out[f"p{p}"] = round(ordered[idx], 2)
    return out


def _doc_def(doc_id: str, *, probe: str | None = None) -> dict[str, Any]:
    schema = [
        {"id": f"f-{uuid.uuid4().hex[:8]}", "name": "total_amount", "description": "Total TTC"},
    ]
    if probe:
        schema.append(
            {"id": f"f-{uuid.uuid4().hex[:8]}", "name": probe, "description": "cache bust"},
        )
    return {
        "id": doc_id,
        "documentType": "Invoice",
        "extractionMode": "document_model",
        "validationMode": "logic_only",
        "documentModelId": REPODY_VLM_CATALOG_ID,
        "schema": schema,
    }


def _snapshot(doc_id: str, *, probe: str | None = None) -> dict[str, Any]:
    rule_id = f"rule-{uuid.uuid4().hex[:6]}"
    return {
        "documents": [_doc_def(doc_id, probe=probe)],
        "rules": [
            {
                "id": rule_id,
                "name": "Total is 6000",
                "kind": "logic",
                "scope": "intra",
                "appliesTo": [doc_id],
                "body": "total_amount == 6000",
                "conditions": [
                    {
                        "id": f"{rule_id}-c1",
                        "left": {"kind": "field", "value": "total_amount"},
                        "operator": "==",
                        "right": {"kind": "literal", "value": "6000"},
                    }
                ],
                "severity": "reject",
            }
        ],
        "workflowName": "stress-test",
    }


async def _record(
    report: StressReport,
    *,
    phase: str,
    method: str,
    path: str,
    status: int,
    latency_ms: float,
    detail: str = "",
) -> None:
    report.http_events.append(
        HttpEvent(phase=phase, method=method, path=path, status=status, latency_ms=latency_ms, detail=detail)
    )


def _parse_json_body(res: httpx.Response) -> dict[str, Any]:
    """Parse health/readiness JSON even when HTTP status is 503 (admission/degraded)."""
    try:
        payload = res.json()
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


async def _healthz(client: httpx.AsyncClient, report: StressReport, t0: float) -> dict[str, Any]:
    start = time.perf_counter()
    res = await client.get("/v1/healthz")
    latency = (time.perf_counter() - start) * 1000
    await _record(report, phase="health", method="GET", path="/v1/healthz", status=res.status_code, latency_ms=latency)
    body = _parse_json_body(res)
    sample = {
        "t_ms": round((time.perf_counter() - t0) * 1000),
        "queuedRuns": body.get("queuedRuns"),
        "runningRuns": body.get("runningRuns"),
        "inflightRuns": body.get("inflightRuns"),
    }
    report.health_samples.append(sample)
    return body


async def _save_workflow(client: httpx.AsyncClient, workflow_id: str, doc_id: str) -> None:
    snap = _snapshot(doc_id)
    res = await client.put(
        f"/v1/workflows/{workflow_id}",
        json={
            "id": workflow_id,
            "name": f"Stress {workflow_id}",
            "description": "stress_test_platform.py",
            "status": "draft",
            "owner": "stress",
            "documents": snap["documents"],
            "rules": snap["rules"],
        },
    )
    res.raise_for_status()


async def _start_valid_run(
    client: httpx.AsyncClient,
    *,
    workflow_id: str,
    doc_id: str,
    binding: dict[str, str],
    probe: str,
) -> tuple[str, float]:
    start = time.perf_counter()
    res = await client.post(
        f"/v1/workflows/{workflow_id}/runs/json",
        json={"snapshot": _snapshot(doc_id, probe=probe), "fileBindings": [binding]},
    )
    latency = (time.perf_counter() - start) * 1000
    res.raise_for_status()
    return res.json()["runId"], latency


async def _multipart_run(
    client: httpx.AsyncClient,
    *,
    workflow_id: str,
    doc_id: str,
    filename: str,
    data: bytes,
    mime: str,
) -> httpx.Response:
    payload = json.dumps(
        {
            "documents": [_doc_def(doc_id)],
            "rules": _snapshot(doc_id)["rules"],
            "workflowName": "stress-invalid",
        }
    )
    return await client.post(
        f"/v1/workflows/{workflow_id}/runs",
        files=[
            ("payload", (None, payload.encode(), "application/json")),
            ("document_ids", (None, json.dumps([doc_id]).encode(), "application/json")),
            ("files", (filename, data, mime)),
        ],
    )


async def _wait_run_terminal(
    client: httpx.AsyncClient,
    run_id: str,
    *,
    timeout_s: float = 300.0,
    poll_s: float = 2.0,
) -> str | None:
    deadline = time.perf_counter() + timeout_s
    while time.perf_counter() < deadline:
        try:
            res = await client.get(f"/v1/runs/{run_id}/status")
            if not res.is_success:
                await asyncio.sleep(_jitter(poll_s))
                continue
            status = str(res.json().get("status") or "")
            if status in ("done", "failed"):
                return status
        except httpx.HTTPError:
            pass
        await asyncio.sleep(_jitter(poll_s))
    return None


async def phase_invalid_files(
    client: httpx.AsyncClient,
    report: StressReport,
    *,
    workflow_id: str,
    doc_id: str,
    pdf_bytes: bytes,
) -> None:
    cases: list[tuple[str, str, bytes, str, int | None]] = [
        ("empty", "empty.txt", b"", "text/plain", 400),
        ("text_not_pdf", "notes.txt", b"hello world not a pdf", "text/plain", 400),
        ("exe_declared", "malware.exe", b"MZfake", "application/octet-stream", 400),
        ("pdf_extension_wrong_content", "fake.pdf", b"not a real pdf at all", "application/pdf", 400),
        ("valid_pdf", "Facture.pdf", pdf_bytes, "application/pdf", 202),
        ("minimal_pdf", "tiny.pdf", _MINIMAL_PDF, "application/pdf", 202),
    ]

    for name, filename, data, mime, expected in cases:
        start = time.perf_counter()
        res = await _multipart_run(
            client,
            workflow_id=workflow_id,
            doc_id=doc_id,
            filename=filename,
            data=data,
            mime=mime,
        )
        latency = (time.perf_counter() - start) * 1000
        await _record(
            report,
            phase="invalid_file",
            method="POST",
            path=f"/v1/workflows/{workflow_id}/runs",
            status=res.status_code,
            latency_ms=latency,
            detail=name,
        )
        ok = expected is None or res.status_code == expected
        body_snip = res.text[:300] if res.text else ""
        report.invalid_file_results.append(
            {
                "case": name,
                "filename": filename,
                "mime": mime,
                "size": len(data),
                "status": res.status_code,
                "expected": expected,
                "pass": ok,
                "body": body_snip,
            }
        )
        if name == "valid_pdf" and res.status_code == 202:
            try:
                run_id = res.json().get("runId")
                if run_id:
                    await _wait_run_terminal(client, str(run_id))
            except (httpx.HTTPError, ValueError, TypeError):
                pass
        elif name == "minimal_pdf" and res.status_code == 503 and expected == 202:
            for attempt in range(8):
                await asyncio.sleep(_jitter(min(30.0, 2.0 ** attempt)))
                retry = await _multipart_run(
                    client,
                    workflow_id=workflow_id,
                    doc_id=doc_id,
                    filename=filename,
                    data=data,
                    mime=mime,
                )
                if retry.status_code == expected:
                    report.invalid_file_results[-1] = {
                        **report.invalid_file_results[-1],
                        "status": retry.status_code,
                        "pass": True,
                        "body": (retry.text[:300] if retry.text else ""),
                    }
                    break
                if retry.status_code not in (429, 503):
                    break

    # Presign with disallowed mime
    start = time.perf_counter()
    presign_res = await client.post(
        "/v1/uploads/presign",
        json={
            "files": [
                {
                    "fileName": "bad.bin",
                    "mimeType": "application/x-msdownload",
                    "size": 128,
                    "documentId": doc_id,
                }
            ]
        },
    )
    latency = (time.perf_counter() - start) * 1000
    await _record(
        report,
        phase="invalid_presign",
        method="POST",
        path="/v1/uploads/presign",
        status=presign_res.status_code,
        latency_ms=latency,
        detail="exe_mime",
    )
    report.invalid_file_results.append(
        {
            "case": "presign_exe_mime",
            "status": presign_res.status_code,
            "expected": 400,
            "pass": presign_res.status_code == 400,
            "body": presign_res.text[:300],
        }
    )


async def _track_run(
    client: httpx.AsyncClient,
    lifecycle: RunLifecycle,
    *,
    t0: float,
    stop: asyncio.Event,
    poll_s: float,
) -> None:
    wait_s = poll_s
    while not stop.is_set():
        try:
            res = await client.get(f"/v1/runs/{lifecycle.run_id}/status")
            if res.status_code == 429:
                retry_s = _retry_after_s(res) or max(_RATE_LIMIT_POLL_S, wait_s * 2)
                wait_s = min(_MAX_POLL_S, retry_s)
                await asyncio.sleep(_jitter(wait_s))
                continue
            if not res.is_success:
                await asyncio.sleep(_jitter(wait_s))
                continue
            body = res.json()
            status = str(body.get("status") or "")
            progress = body.get("progress") or {}
            pos = progress.get("queuePosition")
            depth = progress.get("queueDepth")
            if pos is not None:
                lifecycle.max_queue_position = max(lifecycle.max_queue_position or 0, int(pos))
            if depth is not None:
                lifecycle.max_queue_depth = max(lifecycle.max_queue_depth or 0, int(depth))
            now_ms = round((time.perf_counter() - t0) * 1000)
            if status == "running" and lifecycle.first_running_ms is None:
                lifecycle.first_running_ms = now_ms - lifecycle.enqueued_ms
            if status in ("done", "failed"):
                lifecycle.terminal_ms = now_ms - lifecycle.enqueued_ms
                lifecycle.terminal_status = status
                if status == "failed":
                    lifecycle.error = str(body.get("error") or "")[:500]
                return
            wait_s = min(_MAX_POLL_S, max(_QUEUED_POLL_S if status == "queued" else poll_s, wait_s + 0.25))
        except httpx.HTTPError:
            pass
        await asyncio.sleep(_jitter(wait_s))


async def phase_burst(
    client: httpx.AsyncClient,
    report: StressReport,
    *,
    workflow_id: str,
    doc_id: str,
    binding: dict[str, str],
    burst: int,
    t0: float,
    poll_s: float,
    stop: asyncio.Event,
) -> list[RunLifecycle]:
    lifecycles: list[RunLifecycle] = []
    trackers: list[asyncio.Task[None]] = []

    async def _one(index: int) -> RunLifecycle:
        probe = f"burst_{index}_{uuid.uuid4().hex[:8]}"
        try:
            run_id, enqueue_ms = await _start_valid_run(
                client,
                workflow_id=workflow_id,
                doc_id=doc_id,
                binding=binding,
                probe=probe,
            )
            lc = RunLifecycle(
                run_id=run_id,
                enqueued_ms=round((time.perf_counter() - t0) * 1000),
                enqueue_latency_ms=enqueue_ms,
            )
            trackers.append(asyncio.create_task(_track_run(client, lc, t0=t0, stop=stop, poll_s=poll_s)))
            return lc
        except httpx.HTTPStatusError as exc:
            lc = RunLifecycle(
                run_id=f"rejected-{index}",
                enqueued_ms=round((time.perf_counter() - t0) * 1000),
                enqueue_latency_ms=0,
                terminal_status="rejected",
                error=f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
            )
            await _record(
                report,
                phase="burst_enqueue",
                method="POST",
                path=f"/v1/workflows/{workflow_id}/runs/json",
                status=exc.response.status_code,
                latency_ms=0,
                detail=lc.error,
            )
            return lc

    results = await asyncio.gather(*[_one(i) for i in range(burst)])
    lifecycles.extend(results)
    report.runs.extend([lc for lc in lifecycles if lc.run_id and not lc.run_id.startswith("rejected")])
    return lifecycles


async def phase_random(
    client: httpx.AsyncClient,
    report: StressReport,
    *,
    workflow_id: str,
    doc_id: str,
    binding: dict[str, str],
    pdf_bytes: bytes,
    rounds: int,
    t0: float,
    poll_s: float,
    stop: asyncio.Event,
) -> None:
    rng = random.Random(42)
    actions = ("valid_run", "invalid_upload", "status_noise", "healthz")

    for round_idx in range(rounds):
        action = rng.choice(actions)
        if action == "valid_run":
            probe = f"rnd_{round_idx}_{uuid.uuid4().hex[:6]}"
            try:
                run_id, enqueue_ms = await _start_valid_run(
                    client,
                    workflow_id=workflow_id,
                    doc_id=doc_id,
                    binding=binding,
                    probe=probe,
                )
                lc = RunLifecycle(
                    run_id=run_id,
                    enqueued_ms=round((time.perf_counter() - t0) * 1000),
                    enqueue_latency_ms=enqueue_ms,
                )
                report.runs.append(lc)
                asyncio.create_task(_track_run(client, lc, t0=t0, stop=stop, poll_s=poll_s))
            except httpx.HTTPStatusError as exc:
                await _record(
                    report,
                    phase="random",
                    method="POST",
                    path="/v1/workflows/{workflow_id}/runs/json",
                    status=exc.response.status_code,
                    latency_ms=0,
                    detail=f"valid_run rejected: {exc.response.text[:120]}",
                )
        elif action == "invalid_upload":
            bad = rng.choice(
                [
                    ("x.txt", b"text", "text/plain"),
                    ("empty.pdf", b"", "application/pdf"),
                    ("fake.pdf", b"xxx", "application/pdf"),
                ]
            )
            res = await _multipart_run(
                client,
                workflow_id=workflow_id,
                doc_id=doc_id,
                filename=bad[0],
                data=bad[1],
                mime=bad[2],
            )
            await _record(
                report,
                phase="random",
                method="POST",
                path=f"/v1/workflows/{workflow_id}/runs",
                status=res.status_code,
                latency_ms=0,
                detail=f"invalid:{bad[0]}",
            )
        elif action == "status_noise" and report.runs:
            rid = rng.choice(report.runs).run_id
            start = time.perf_counter()
            res = await client.get(f"/v1/runs/{rid}/status")
            await _record(
                report,
                phase="random",
                method="GET",
                path=f"/v1/runs/{rid}/status",
                status=res.status_code,
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        else:
            await _healthz(client, report, t0)

        await asyncio.sleep(rng.uniform(0.05, 0.35))


async def _wait_drain(
    client: httpx.AsyncClient,
    report: StressReport,
    *,
    t0: float,
    timeout_s: float,
    poll_s: float,
) -> None:
    deadline = time.perf_counter() + timeout_s
    idle_streak = 0
    while time.perf_counter() < deadline:
        body = await _healthz(client, report, t0)
        queued = int(body.get("queuedRuns") or 0)
        running = int(body.get("runningRuns") or 0)
        inflight = int(body.get("inflightRuns") or 0)
        if queued == 0 and running == 0 and inflight == 0:
            idle_streak += 1
            if idle_streak >= 3:
                return
        else:
            idle_streak = 0
        await asyncio.sleep(poll_s)
    raise TimeoutError(f"Queue did not drain within {timeout_s:.0f}s")


def _build_summary(report: StressReport, *, wall_ms: float) -> dict[str, Any]:
    invalid_pass = sum(1 for r in report.invalid_file_results if r.get("pass"))
    invalid_total = len(report.invalid_file_results)

    enqueue_latencies = [r.enqueue_latency_ms for r in report.runs if r.enqueue_latency_ms > 0]
    queue_waits = [r.first_running_ms for r in report.runs if r.first_running_ms is not None]
    run_durations = [r.terminal_ms for r in report.runs if r.terminal_ms is not None]
    done = sum(1 for r in report.runs if r.terminal_status == "done")
    failed = sum(1 for r in report.runs if r.terminal_status == "failed")
    pending = sum(1 for r in report.runs if r.terminal_status is None)

    status_counts: dict[str, int] = {}
    for ev in report.http_events:
        key = str(ev.status)
        status_counts[key] = status_counts.get(key, 0) + 1

    max_depth = max((r.max_queue_depth or 0 for r in report.runs), default=0)
    max_pos = max((r.max_queue_position or 0 for r in report.runs), default=0)

    health_queued = [int(h.get("queuedRuns") or 0) for h in report.health_samples]
    health_running = [int(h.get("runningRuns") or 0) for h in report.health_samples]

    throughput = (done / (wall_ms / 60000)) if wall_ms > 0 and done else 0.0

    return {
        "wallMs": round(wall_ms),
        "invalidFilesPass": f"{invalid_pass}/{invalid_total}",
        "runsSubmitted": len(report.runs),
        "runsDone": done,
        "runsFailed": failed,
        "runsPending": pending,
        "throughputRunsPerMinute": round(throughput, 2),
        "enqueueLatencyMs": _percentiles(enqueue_latencies),
        "queueWaitMs": _percentiles([float(v) for v in queue_waits]),
        "totalRunMs": _percentiles([float(v) for v in run_durations]),
        "maxObservedQueueDepth": max_depth,
        "maxObservedQueuePosition": max_pos,
        "healthMaxQueued": max(health_queued) if health_queued else 0,
        "healthMaxRunning": max(health_running) if health_running else 0,
        "httpStatusCounts": status_counts,
        "rateLimitOrAdmissionHits": status_counts.get("429", 0) + status_counts.get("503", 0),
    }


async def run_stress(args: argparse.Namespace) -> int:
    pdf_path = args.document
    if not pdf_path.is_file():
        print(f"Missing document: {pdf_path}", file=sys.stderr)
        return 2

    pdf_bytes = pdf_path.read_bytes()
    timeout = httpx.Timeout(120.0, connect=15.0)
    workflow_id = f"wf-stress-{uuid.uuid4().hex[:8]}"
    doc_id = f"doc-{uuid.uuid4().hex[:6]}"
    report = StressReport(
        started_at=datetime.now(UTC).isoformat(),
        api=args.api.rstrip("/"),
        config=vars(args),
    )
    stop = asyncio.Event()
    t0 = time.perf_counter()
    wall_start = t0

    headers = {"Authorization": f"Bearer {args.bearer_token}"} if args.bearer_token else None
    async with httpx.AsyncClient(
        base_url=args.api.rstrip("/"),
        headers=headers,
        timeout=timeout,
    ) as client:
        await _save_workflow(client, workflow_id, doc_id)
        binding = await _upload_presign(
            client,
            doc_id=doc_id,
            filename="Facture.pdf",
            data=pdf_bytes,
            mime="application/pdf",
        )

        print("Phase 1: invalid / unsupported files …")
        await phase_invalid_files(client, report, workflow_id=workflow_id, doc_id=doc_id, pdf_bytes=pdf_bytes)

        print(f"Phase 2: burst enqueue ({args.burst} concurrent) …")
        await phase_burst(
            client,
            report,
            workflow_id=workflow_id,
            doc_id=doc_id,
            binding=binding,
            burst=args.burst,
            t0=t0,
            poll_s=args.poll_interval_s,
            stop=stop,
        )

        print(f"Phase 3: random mixed load ({args.random_rounds} rounds) …")
        await phase_random(
            client,
            report,
            workflow_id=workflow_id,
            doc_id=doc_id,
            binding=binding,
            pdf_bytes=pdf_bytes,
            rounds=args.random_rounds,
            t0=t0,
            poll_s=args.poll_interval_s,
            stop=stop,
        )

        print("Phase 4: drain queue …")
        try:
            await _wait_drain(
                client,
                report,
                t0=t0,
                timeout_s=args.timeout_seconds,
                poll_s=max(args.poll_interval_s, 1.0),
            )
        except TimeoutError as exc:
            print(f"  WARNING: {exc}", file=sys.stderr)
        finally:
            stop.set()
            await asyncio.sleep(1.0)

        try:
            await client.delete(f"/v1/workflows/{workflow_id}")
        except httpx.HTTPError:
            pass

    wall_ms = (time.perf_counter() - wall_start) * 1000
    report.summary = _build_summary(report, wall_ms=wall_ms)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "startedAt": report.started_at,
        "api": report.api,
        "config": {
            k: "<redacted>" if "token" in k.lower() else str(v) if isinstance(v, Path) else v
            for k, v in report.config.items()
            if not callable(v)
        },
        "summary": report.summary,
        "invalidFileResults": report.invalid_file_results,
        "runs": [r.__dict__ for r in report.runs],
        "healthSamples": report.health_samples,
        "httpEventCount": len(report.http_events),
    }
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    s = report.summary
    print("\n=== Stress test summary ===")
    print(f"  Wall time:           {s['wallMs']} ms")
    print(f"  Invalid file checks: {s['invalidFilesPass']}")
    print(f"  Runs submitted:      {s['runsSubmitted']}  done={s['runsDone']}  failed={s['runsFailed']}  pending={s['runsPending']}")
    print(f"  Throughput:          {s['throughputRunsPerMinute']} runs/min")
    print(f"  Max queue depth:     {s['maxObservedQueueDepth']} (health max queued={s['healthMaxQueued']})")
    print(f"  Enqueue latency ms:  {s['enqueueLatencyMs']}")
    print(f"  Queue wait ms:       {s['queueWaitMs']}")
    print(f"  Total run ms:        {s['totalRunMs']}")
    print(f"  429/503 hits:        {s['rateLimitOrAdmissionHits']}")
    print(f"  HTTP status counts:  {s['httpStatusCounts']}")
    print(f"\nReport: {args.output}")

    if s["runsPending"] > 0:
        return 1
    if s["invalidFilesPass"] != f"{len(report.invalid_file_results)}/{len(report.invalid_file_results)}":
        return 1
    return 0


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--bearer-token",
        default=None,
        help="OIDC access token for auth-enabled stacks.",
    )
    parser.add_argument("--document", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--burst", type=int, default=8, help="Concurrent valid runs enqueued at once")
    parser.add_argument("--random-rounds", type=int, default=20, help="Random mixed-traffic rounds")
    parser.add_argument("--poll-interval-s", type=float, default=0.75)
    parser.add_argument("--timeout-seconds", type=float, default=1200.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "benchmark-reports" / "stress-test.json",
    )
