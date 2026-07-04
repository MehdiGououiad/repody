"""
Python mirror of the browser UI workflow-run flow (lib/api/workflow-run.ts + run-poll.ts).

Same presigned upload, /runs/json, and poll sequence the Test tab uses.
"""

from __future__ import annotations

import asyncio
import json
import random
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

MAX_POLL_WAIT_S = 8.0
RATE_LIMIT_POLL_WAIT_S = 4.0


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


def _next_poll_wait_s(current_s: float, body: dict[str, Any]) -> float:
    progress = body.get("progress") or {}
    queued = body.get("status") == "queued" or progress.get("queuePosition") is not None
    floor = RATE_LIMIT_POLL_WAIT_S if queued else interval_floor_s(current_s)
    return min(MAX_POLL_WAIT_S, max(floor, current_s + 0.2))


def interval_floor_s(current_s: float) -> float:
    return min(2.0, max(0.4, current_s))


async def _request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_attempts: int = 8,
    retry_wait_s: float = 2.0,
) -> httpx.Response:
    """Retry transient transport errors during long-running poll loops."""
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            response = await client.request(method, url)
            response.raise_for_status()
            return response
        except httpx.TransportError as exc:
            last_exc = exc
            if attempt + 1 >= max_attempts:
                break
            await asyncio.sleep(retry_wait_s * (attempt + 1))
        except httpx.HTTPStatusError:
            raise
    assert last_exc is not None
    raise last_exc


async def poll_run_until_done(
    client: httpx.AsyncClient,
    run_id: str,
    *,
    max_ms: float = 300_000,
    interval_ms: float = 400,
) -> dict[str, Any]:
    """Poll GET /v1/runs/{id}/status until done, then GET /v1/runs/{id} for full result."""
    import os

    env_interval = os.getenv("AUDIT_TEST_POLL_INTERVAL_MS", "").strip()
    if env_interval:
        try:
            interval_ms = float(env_interval)
        except ValueError:
            pass
    deadline = asyncio.get_event_loop().time() + max_ms / 1000
    wait_s = interval_ms / 1000
    while asyncio.get_event_loop().time() < deadline:
        status_res = await client.get(f"/v1/runs/{run_id}/status")
        if status_res.status_code == 429:
            retry_s = _retry_after_s(status_res) or max(RATE_LIMIT_POLL_WAIT_S, wait_s * 2)
            wait_s = min(MAX_POLL_WAIT_S, retry_s)
            await asyncio.sleep(_jitter(wait_s))
            continue
        status_res.raise_for_status()
        body = status_res.json()
        if body.get("status") == "done":
            detail_res = await _request_with_retry(client, "GET", f"/v1/runs/{run_id}")
            detail = detail_res.json()
            if not detail.get("result"):
                raise RuntimeError("Run finished without result payload")
            return detail["result"]
        if body.get("status") == "failed":
            raise RuntimeError(body.get("error") or "Run failed")
        wait_s = _next_poll_wait_s(wait_s, body)
        await asyncio.sleep(_jitter(wait_s))
    raise TimeoutError(
        f"Run {run_id} timed out after {max_ms}ms — check worker and Model Runner logs"
    )


async def run_test_with_files(
    client: httpx.AsyncClient,
    workflow_id: str,
    *,
    documents: list[dict[str, Any]],
    rules: list[dict[str, Any]],
    workflow_name: str,
    files_by_doc_id: dict[str, tuple[str, bytes, str]],
    max_wait_ms: float = 300_000,
) -> dict[str, Any]:
    """
    Same contract as UI runTestWithFiles():
      POST /v1/uploads/presign
      PUT direct-to-storage for each file
      POST /v1/uploads/confirm
      POST /v1/workflows/{id}/runs/json
      poll until done
    """
    doc_order = [
        d["id"]
        for d in documents
        if (d.get("documentType") or "").strip() and d["id"] in files_by_doc_id
    ]
    payload_json = json.dumps(
        {
            "documents": documents,
            "rules": rules,
            "workflowName": workflow_name,
        }
    )

    presign = await client.post(
        "/v1/uploads/presign",
        json={
            "files": [
                {
                    "fileName": files_by_doc_id[doc_id][0],
                    "mimeType": files_by_doc_id[doc_id][2],
                    "size": len(files_by_doc_id[doc_id][1]),
                    "documentId": doc_id,
                }
                for doc_id in doc_order
            ]
        },
    )
    presign.raise_for_status()
    presigned = presign.json()
    if presigned.get("uploadMode") != "presigned":
        raise RuntimeError("Presigned uploads are not available.")

    uploads = presigned["uploads"]
    async with httpx.AsyncClient(timeout=120.0) as raw_client:
        for item in uploads:
            doc_id = item.get("documentId") or ""
            filename, data, mime = files_by_doc_id[doc_id]
            put = await raw_client.put(
                item["uploadUrl"],
                content=data,
                headers=item.get("headers") or {"Content-Type": mime},
            )
            if put.status_code not in (200, 204):
                raise RuntimeError(f"PUT upload failed for {filename}: {put.status_code}")

    confirm = await client.post(
        "/v1/uploads/confirm",
        json={"storageKeys": [item["storageKey"] for item in uploads]},
    )
    confirm.raise_for_status()
    confirmed = confirm.json()["uploads"]
    file_bindings = [
        {
            "documentId": item.get("documentId") or "",
            "storageKey": item["storageKey"],
            "mimeType": confirmed_item["mimeType"],
            "fileName": confirmed_item["fileName"],
        }
        for item, confirmed_item in zip(uploads, confirmed, strict=True)
    ]

    start = await client.post(
        f"/v1/workflows/{workflow_id}/runs/json",
        json={"snapshot": json.loads(payload_json), "fileBindings": file_bindings},
    )
    if start.status_code != 202:
        raise RuntimeError(f"POST runs/json failed {start.status_code}: {start.text}")

    run_id = start.json()["runId"]

    return await poll_run_until_done(client, run_id, max_ms=max_wait_ms)


async def save_workflow(
    client: httpx.AsyncClient,
    *,
    wf_id: str,
    name: str,
    documents: list[dict[str, Any]],
    rules: list[dict[str, Any]],
    owner: str = "pytest",
) -> str:
    """PUT upserts full workflow config (same as builder save)."""
    updated = await client.put(
        f"/v1/workflows/{wf_id}",
        json={
            "id": wf_id,
            "name": name,
            "description": "ui-flow e2e",
            "status": "draft",
            "owner": owner,
            "documents": documents,
            "rules": rules,
        },
    )
    updated.raise_for_status()
    for _ in range(8):
        check = await client.get(f"/v1/workflows/{wf_id}")
        if check.status_code == 200:
            return wf_id
        await asyncio.sleep(0.25)
    check.raise_for_status()
    return wf_id
