"""Live-stack API E2E suite — requires running Docker stack (Hatchet + workers + Model Runner).

Run: pnpm test:api:live
"""

from __future__ import annotations

import json
import os
import time
import uuid

import httpx
import pytest

from tests.test_e2e.facture_helpers import (
    EXPECTED_TOTAL,
    FACTURE_UI_PATHS,
    WORKFLOW_NAME,
    document_def,
    facture_bytes,
    rules_for_case,
    total_from_result,
)

DOCUMENT_MODEL_CASE = FACTURE_UI_PATHS[0]

BASE = os.environ.get("E2E_API_URL", "http://localhost:8000").rstrip("/")
pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE, timeout=120.0) as c:
        yield c


def test_live_health_hatchet(client: httpx.Client):
    res = client.get("/v1/healthz")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["queueBackend"] == "hatchet"
    assert body.get("hatchetConfigured") is True


def test_live_workflows_and_metrics(client: httpx.Client):
    assert client.get("/v1/workflows").status_code == 200
    assert client.get("/v1/metrics").status_code == 200
    assert client.get("/v1/rules/library").status_code == 200


def test_live_facture_document_model_run(client: httpx.Client):
    suffix = uuid.uuid4().hex[:8]
    wf_id = f"wf-live-api-{suffix}"
    doc_id = f"doc-live-{suffix}"
    pdf = facture_bytes()

    put = client.put(
        f"/v1/workflows/{wf_id}",
        json={
            "id": wf_id,
            "name": WORKFLOW_NAME,
            "description": "live api e2e",
            "status": "draft",
            "owner": "live-e2e",
            "documents": [document_def(DOCUMENT_MODEL_CASE, doc_id=doc_id)],
            "rules": rules_for_case(DOCUMENT_MODEL_CASE),
        },
    )
    assert put.status_code == 200

    payload = json.dumps(
        {
            "documents": [document_def(DOCUMENT_MODEL_CASE, doc_id=doc_id)],
            "rules": rules_for_case(DOCUMENT_MODEL_CASE),
            "workflowName": WORKFLOW_NAME,
        }
    )
    started = client.post(
        f"/v1/workflows/{wf_id}/runs",
        files=[
            ("payload", (None, payload.encode(), "application/json")),
            ("document_ids", (None, json.dumps([doc_id]).encode(), "application/json")),
            ("files", ("Facture.pdf", pdf, "application/pdf")),
        ],
    )
    assert started.status_code == 202
    run_id = started.json()["runId"]

    deadline = time.time() + 900
    last_error = None
    while time.time() < deadline:
        poll = client.get(f"/v1/runs/{run_id}/status")
        poll.raise_for_status()
        body = poll.json()
        status = body.get("status")
        if status == "done":
            detail = client.get(f"/v1/runs/{run_id}").json()
            result = detail.get("result")
            assert result is not None, detail
            assert total_from_result(result) == EXPECTED_TOTAL
            return
        if status == "failed":
            last_error = body.get("error") or "run failed"
            break
        time.sleep(2.0)

    pytest.fail(last_error or f"Run {run_id} timed out")
