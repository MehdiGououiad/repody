"""Queue depth benchmark — use via benchmark_dev.py queue."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_BACKEND = Path(__file__).resolve().parents[1]
for _path in (_BACKEND / "src", _BACKEND):
    _text = str(_path)
    if _text not in sys.path:
        sys.path.insert(0, _text)

import httpx  # noqa: E402

from audit_workbench.extraction.model_registry import REPODY_VLM_CATALOG_ID  # noqa: E402
from scripts.benchmark_ui_route import (  # noqa: E402
    DEFAULT_PDF,
    _fetch_oidc_token,
    _upload_presign,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Sample:
    t_ms: int
    run_id: str
    status: str
    queue_position: int | None
    queue_depth: int | None
    label: str | None
    source: str


@dataclass
class RunTracker:
    run_id: str
    samples: list[Sample] = field(default_factory=list)
    sse_samples: list[Sample] = field(default_factory=list)


async def _save_workflow_once(
    client: httpx.AsyncClient,
    *,
    workflow_id: str,
    doc_id: str,
) -> None:
    documents = [
        {
            "id": doc_id,
            "documentType": "Invoice",
            "extractionMode": "document_model",
            "validationMode": "logic_only",
            "ocrModel": REPODY_VLM_CATALOG_ID,
            "schema": [
                {"id": f"f-{uuid.uuid4().hex[:8]}", "name": "total_amount", "description": "Total TTC"},
            ],
        }
    ]
    rules = [
        {
            "id": f"rule-{uuid.uuid4().hex[:6]}",
            "name": "Total is 6000",
            "kind": "logic",
            "scope": "intra",
            "appliesTo": [doc_id],
            "body": "total_amount == 6000",
            "severity": "reject",
        }
    ]
    save_res = await client.put(
        f"/v1/workflows/{workflow_id}",
        json={
            "id": workflow_id,
            "name": f"Queue bench {workflow_id}",
            "description": "benchmark_queue.py",
            "status": "draft",
            "owner": "benchmark",
            "documents": documents,
            "rules": rules,
        },
    )
    save_res.raise_for_status()


def _run_snapshot(*, doc_id: str, probe: str, workflow_id: str) -> dict[str, Any]:
    documents = [
        {
            "id": doc_id,
            "documentType": "Invoice",
            "extractionMode": "document_model",
            "validationMode": "logic_only",
            "ocrModel": REPODY_VLM_CATALOG_ID,
            "schema": [
                {"id": f"f-{uuid.uuid4().hex[:8]}", "name": "total_amount", "description": "Total TTC"},
                {"id": f"f-{uuid.uuid4().hex[:8]}", "name": probe, "description": "cache bust"},
            ],
        }
    ]
    rules = [
        {
            "id": f"rule-{uuid.uuid4().hex[:6]}",
            "name": "Total is 6000",
            "kind": "logic",
            "scope": "intra",
            "appliesTo": [doc_id],
            "body": "total_amount == 6000",
            "severity": "reject",
        }
    ]
    return {"documents": documents, "rules": rules, "workflowName": f"Queue bench {workflow_id}"}


async def _start_run(
    client: httpx.AsyncClient,
    *,
    workflow_id: str,
    snapshot: dict[str, Any],
    binding: dict[str, Any],
) -> str:
    res = await client.post(
        f"/v1/workflows/{workflow_id}/runs/json",
        json={"snapshot": snapshot, "fileBindings": [binding]},
    )
    res.raise_for_status()
    return res.json()["runId"]


async def _poll_status(
    client: httpx.AsyncClient,
    run_id: str,
    *,
    refresh_token: Callable[[], str] | None = None,
) -> dict[str, Any]:
    res = await client.get(f"/v1/runs/{run_id}/status")
    if res.status_code == 401 and refresh_token is not None:
        client.headers["Authorization"] = f"Bearer {refresh_token()}"
        res = await client.get(f"/v1/runs/{run_id}/status")
    res.raise_for_status()
    return res.json()


async def _wait_all_done(
    client: httpx.AsyncClient,
    run_ids: list[str],
    *,
    timeout_s: float,
    interval_s: float,
    observe_s: float | None,
    refresh_token: Callable[[], str] | None,
) -> None:
    deadline = time.perf_counter() + (observe_s if observe_s is not None else timeout_s)
    while time.perf_counter() < deadline:
        statuses: list[str] = []
        for run_id in run_ids:
            try:
                body = await _poll_status(client, run_id, refresh_token=refresh_token)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    await asyncio.sleep(2.0)
                    continue
                raise
            statuses.append(str(body.get("status") or ""))
        if observe_s is None and statuses and all(s in ("done", "failed") for s in statuses):
            return
        await asyncio.sleep(interval_s)
    if observe_s is None:
        raise TimeoutError("runs did not finish before timeout")


async def _watch_sse(
    client: httpx.AsyncClient,
    run_id: str,
    tracker: RunTracker,
    stop: asyncio.Event,
    started_ms: int,
) -> None:
    url = f"/v1/runs/{run_id}/events"
    try:
        async with client.stream("GET", url, timeout=None) as stream:
            async for line in stream.aiter_lines():
                if stop.is_set():
                    break
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if not raw:
                    continue
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                progress = payload.get("progress") or {}
                tracker.sse_samples.append(
                    Sample(
                        t_ms=round((time.perf_counter() * 1000) - started_ms),
                        run_id=run_id,
                        status=str(payload.get("status") or ""),
                        queue_position=progress.get("queuePosition"),
                        queue_depth=progress.get("queueDepth"),
                        label=progress.get("label"),
                        source="sse",
                    )
                )
                if payload.get("terminal"):
                    break
    except httpx.HTTPError:
        return


async def _poll_loop(
    client: httpx.AsyncClient,
    trackers: dict[str, RunTracker],
    stop: asyncio.Event,
    started_ms: int,
    interval_s: float,
    refresh_token: Callable[[], str] | None,
) -> None:
    last: dict[str, tuple[Any, ...]] = {}
    while not stop.is_set():
        for run_id, tracker in trackers.items():
            try:
                body = await _poll_status(client, run_id, refresh_token=refresh_token)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    continue
                continue
            progress = body.get("progress") or {}
            key = (
                body.get("status"),
                progress.get("queuePosition"),
                progress.get("queueDepth"),
                progress.get("label"),
            )
            if last.get(run_id) == key:
                continue
            last[run_id] = key
            tracker.samples.append(
                Sample(
                    t_ms=round((time.perf_counter() * 1000) - started_ms),
                    run_id=run_id,
                    status=str(body.get("status") or ""),
                    queue_position=progress.get("queuePosition"),
                    queue_depth=progress.get("queueDepth"),
                    label=progress.get("label"),
                    source="poll",
                )
            )
        await asyncio.sleep(interval_s)


async def run_benchmark(args: argparse.Namespace) -> int:
    pdf = args.document
    if not pdf.is_file():
        print(f"Missing PDF: {pdf}", file=sys.stderr)
        return 2

    def refresh_token() -> str:
        new = _fetch_oidc_token(
            keycloak=args.keycloak,
            realm=args.realm,
            client_id=args.client_id,
            client_secret=args.client_secret,
            username=args.username,
            password=args.password,
        )
        if not new:
            raise RuntimeError("Failed to refresh OIDC token")
        return new

    token = refresh_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    timeout = httpx.Timeout(120.0, connect=15.0)
    pdf_bytes = pdf.read_bytes()

    workflow_id = f"wf-queue-{uuid.uuid4().hex[:8]}"
    doc_id = f"doc-{uuid.uuid4().hex[:6]}"
    trackers: dict[str, RunTracker] = {}
    run_ids: list[str] = []

    async with httpx.AsyncClient(base_url=args.api.rstrip("/"), headers=headers, timeout=timeout) as client:
        await _save_workflow_once(client, workflow_id=workflow_id, doc_id=doc_id)
        binding = await _upload_presign(
            client,
            doc_id=doc_id,
            filename="Facture.pdf",
            data=pdf_bytes,
            mime="application/pdf",
        )

        print(f"Queue benchmark @ {args.api} — enqueueing {args.runs} runs…")
        enqueue_started = time.perf_counter()
        for index in range(args.runs):
            probe = f"probe_{index}_{uuid.uuid4().hex[:8]}"
            snapshot = _run_snapshot(doc_id=doc_id, probe=probe, workflow_id=workflow_id)
            run_id = await _start_run(client, workflow_id=workflow_id, snapshot=snapshot, binding=binding)
            run_ids.append(run_id)
            trackers[run_id] = RunTracker(run_id=run_id)
            print(f"  started {index + 1}/{args.runs}: {run_id}")
        enqueue_ms = round((time.perf_counter() - enqueue_started) * 1000)
        print(f"  all enqueued in {enqueue_ms} ms")

        started_ms = time.perf_counter() * 1000
        stop = asyncio.Event()
        poll_task = asyncio.create_task(
            _poll_loop(client, trackers, stop, started_ms, args.poll_interval_s, refresh_token)
        )
        sse_run_id = run_ids[-1]
        sse_task = asyncio.create_task(
            _watch_sse(client, sse_run_id, trackers[sse_run_id], stop, started_ms)
        )

        try:
            await _wait_all_done(
                client,
                run_ids,
                timeout_s=args.timeout_seconds,
                interval_s=max(args.poll_interval_s, 0.5),
                observe_s=args.observe_seconds,
                refresh_token=refresh_token,
            )
        finally:
            stop.set()
            await asyncio.gather(poll_task, sse_task, return_exceptions=True)

        try:
            await client.delete(f"/v1/workflows/{workflow_id}")
        except httpx.HTTPError:
            pass

    report = {
        "generatedAt": datetime.now(UTC).isoformat(),
        "api": args.api,
        "runsEnqueued": args.runs,
        "enqueueMs": enqueue_ms,
        "runIds": run_ids,
        "sseRunId": sse_run_id,
        "trackers": {
            rid: {
                "poll": [s.__dict__ for s in t.samples],
                "sse": [s.__dict__ for s in t.sse_samples],
            }
            for rid, t in trackers.items()
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n--- Queue position timeline (poll) ---")
    for rid in run_ids:
        queued = [s for s in trackers[rid].samples if s.status == "queued"]
        if not queued:
            print(f"  {rid}: never queued (ran immediately)")
            continue
        positions = sorted({s.queue_position for s in queued if s.queue_position is not None})
        depths = sorted({s.queue_depth for s in queued if s.queue_depth is not None})
        print(
            f"  {rid}: queued samples={len(queued)} "
            f"positions={positions} depths={depths} "
            f"first={queued[0].queue_position}/{queued[0].queue_depth} @ {queued[0].t_ms}ms"
        )

    sse = trackers[sse_run_id].sse_samples
    print(f"\n--- SSE on last run ({sse_run_id}) ---")
    print(f"  events with progress: {len(sse)}")
    if sse:
        q = [s for s in sse if s.queue_depth and s.queue_depth > 1]
        print(f"  multi-deep queue events: {len(q)}")
        for s in q[:8]:
            print(f"    t={s.t_ms}ms pos={s.queue_position}/{s.queue_depth} label={s.label!r}")

    print(f"\nReport: {args.output}")
    return 0


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--document", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--runs", type=int, default=4)
    parser.add_argument("--poll-interval-s", type=float, default=0.75)
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    parser.add_argument(
        "--observe-seconds",
        type=float,
        default=None,
        help="Stop after N seconds (queue snapshot; skips waiting for completion)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "benchmark-reports" / "queue-benchmark.json",
    )
    parser.add_argument("--keycloak", default="http://127.0.0.1:8080")
    parser.add_argument("--realm", default="repody")
    parser.add_argument("--client-id", default="repody-web")
    parser.add_argument("--client-secret", default="repody-web-dev-secret")
    parser.add_argument("--username", default="operator@repody.local")
    parser.add_argument("--password", default="repody-dev")
