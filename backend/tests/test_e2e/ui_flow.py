"""
Python mirror of the browser UI test-run flow (lib/api/test-run.ts + run-poll.ts).

Same endpoints, multipart shape, and poll sequence the Test tab uses.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import httpx

from audit_workbench.settings import get_settings


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
    deadline = asyncio.get_event_loop().time() + max_ms / 1000
    wait_s = interval_ms / 1000
    while asyncio.get_event_loop().time() < deadline:
        status_res = await _request_with_retry(client, "GET", f"/v1/runs/{run_id}/status")
        body = status_res.json()
        if body.get("status") == "done":
            detail_res = await _request_with_retry(client, "GET", f"/v1/runs/{run_id}")
            detail = detail_res.json()
            if not detail.get("result"):
                raise RuntimeError("Run finished without result payload")
            return detail["result"]
        if body.get("status") == "failed":
            raise RuntimeError(body.get("error") or "Run failed")
        await asyncio.sleep(wait_s)
        wait_s = min(2.0, wait_s + 0.2)
    raise TimeoutError(f"Run {run_id} timed out after {max_ms}ms — check worker and Model Runner logs")


async def _process_run_inline(run_id: str) -> None:
    """Process a queued run in-process (tests with AUDIT_RUN_JOBS_INLINE=true)."""
    import audit_workbench.db.base as db_base
    from audit_workbench.services.run_processor import process_run

    async with db_base.async_session_factory() as session:
        try:
            await process_run(session, run_id)
            await session.commit()
        except Exception:
            await session.rollback()
            raise


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
      POST /v1/workflows/{id}/runs?mode=test
      multipart: payload, document_ids, files[]
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
    multipart: list[tuple[str, tuple[str, bytes, str]]] = [
        ("payload", (None, payload_json.encode(), "application/json")),
        ("document_ids", (None, json.dumps(doc_order).encode(), "application/json")),
    ]
    for doc_id in doc_order:
        filename, data, mime = files_by_doc_id[doc_id]
        multipart.append(("files", (filename, data, mime)))

    start = await client.post(
        f"/v1/workflows/{workflow_id}/runs?mode=test",
        files=multipart,
    )
    if start.status_code != 202:
        raise RuntimeError(f"POST runs failed {start.status_code}: {start.text}")

    run_id = start.json()["runId"]

    settings = get_settings()
    # ASGI tests without Hatchet workers: drain queued runs in-process when inline.
    if not settings.run_jobs_inline and os.environ.get("E2E_STACK") != "1":
        await _process_run_inline(run_id)

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
    return wf_id
