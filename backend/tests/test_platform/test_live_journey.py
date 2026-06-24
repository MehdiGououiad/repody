"""Full platform API journey against a running stack (not in-memory SQLite).

Run via: pnpm test:platform  (or pytest -m live with E2E_API_URL set)
"""

from __future__ import annotations

import time
import uuid

import httpx
import pytest

from audit_workbench.db.seed import SEED_WORKFLOW_ID
from tests.helpers.live_stack import (
    assert_metrics_access,
    create_anonymous_live_client,
    create_live_client,
    live_api_base,
    live_oidc_enabled,
)

BASE = live_api_base()
WF_ID = SEED_WORKFLOW_ID

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def client():
    with create_live_client() as c:
        yield c


def test_healthz(client: httpx.Client):
    res = client.get("/v1/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_metrics_and_rules_library(client: httpx.Client):
    oidc = live_oidc_enabled(client)
    metrics = client.get("/v1/metrics")
    assert_metrics_access(metrics, oidc_enabled=oidc)

    rules = client.get("/v1/rules/library")
    assert rules.status_code == 200
    assert len(rules.json()["rules"]) >= 1


def test_workflows_list_detail_and_seed_audit(client: httpx.Client):
    listed = client.get("/v1/workflows")
    assert listed.status_code == 200
    workflows = listed.json()["workflows"]
    assert any(w["id"] == WF_ID for w in workflows)

    detail = client.get(f"/v1/workflows/{WF_ID}")
    assert detail.status_code == 200
    assert detail.json()["workflow"]["id"] == WF_ID

    audits = client.get("/v1/audits")
    assert audits.status_code == 200
    assert isinstance(audits.json()["audits"], list)

    # Seed audit may be outside the latest-100 list after many test runs; fetch directly.
    report = client.get("/v1/audits/AUD-2023-8902")
    assert report.status_code == 200
    audit = report.json()
    assert audit["status"] == "failed"
    assert any(r["name"] == "Math integrity" for r in audit.get("ruleResults", []))


def test_dry_run_test_run_and_crud_deploy(client: httpx.Client):
    dry = client.post(
        f"/v1/workflows/{WF_ID}/dry-run",
        json={
            "fields": [
                {"id": "1", "name": "subtotal", "description": "", "sampleValue": "5625"},
                {"id": "2", "name": "tax", "description": "", "sampleValue": "478.13"},
                {"id": "3", "name": "total_amount", "description": "", "sampleValue": "6200"},
            ],
            "rules": [
                {
                    "id": "r1",
                    "name": "Math",
                    "kind": "logic",
                    "body": "subtotal + tax == total_amount",
                    "severity": "reject",
                }
            ],
        },
    )
    assert dry.status_code == 200
    assert dry.json()["ruleResults"][0]["status"] == "failed"

    test_run = client.post(
        f"/v1/workflows/{WF_ID}/runs/json",
        json={
            "snapshot": {
                "documents": [],
                "rules": [],
                "workflowName": "Invoice Audit Pipeline",
            }
        },
    )
    assert test_run.status_code == 202
    run_id = test_run.json()["runId"]

    deadline = time.time() + 120
    audit_id = None
    while time.time() < deadline:
        poll = client.get(f"/v1/runs/{run_id}")
        assert poll.status_code == 200
        body = poll.json()
        if body["status"] == "done" and body.get("result"):
            audit_id = body["result"]["id"]
            assert body["result"]["status"] in ("passed", "failed", "warning")
            break
        if body["status"] == "failed":
            pytest.fail(body.get("error") or "run failed")
        time.sleep(0.5)
    assert audit_id is not None

    detail = client.get(f"/v1/audits/{audit_id}")
    assert detail.status_code == 200

    created = client.post(
        "/v1/workflows",
        json={"name": "Platform E2E WF", "description": "live", "owner": "e2e"},
    )
    assert created.status_code == 201
    wf = created.json()["workflow"]
    wf_id = wf["id"]
    suffix = uuid.uuid4().hex[:8]
    doc_id = f"doc-e2e-{suffix}"
    field_id = f"f-e2e-{suffix}"
    rule_id = f"rule-e2e-{suffix}"

    updated = client.put(
        f"/v1/workflows/{wf_id}",
        json={
            "id": wf_id,
            "name": wf["name"],
            "description": wf.get("description", ""),
            "status": wf.get("status", "draft"),
            "owner": wf.get("owner", "e2e"),
            "documents": [
                {
                    "id": doc_id,
                    "documentType": "Invoice",
                    "schema": [{"id": field_id, "name": "total_amount", "description": "Total"}],
                }
            ],
            "rules": [
                {
                    "id": rule_id,
                    "name": "Positive total",
                    "kind": "logic",
                    "scope": "intra",
                    "appliesTo": [doc_id],
                    "body": "total_amount > 0",
                    "severity": "reject",
                }
            ],
        },
    )
    assert updated.status_code == 200

    deployed = client.post(f"/v1/workflows/{wf_id}/deploy", json={})
    assert deployed.status_code == 200
    assert deployed.json()["workflow"]["deployedAt"]


def test_api_run_poll(client: httpx.Client):
    deployed = client.post(f"/v1/workflows/{WF_ID}/deploy", json={})
    assert deployed.status_code == 200
    key = deployed.json()["workflow"]["apiKey"]
    assert key

    with create_anonymous_live_client() as anon:
        unauthorized = anon.post(f"/v1/workflows/{WF_ID}/runs")
        assert unauthorized.status_code == 401

        started = None
        for _ in range(5):
            started = anon.post(
                f"/v1/workflows/{WF_ID}/runs",
                headers={"Authorization": f"Bearer {key}"},
            )
            if started.status_code == 202:
                break
            time.sleep(0.3)
    assert started is not None and started.status_code == 202
    run_id = started.json()["runId"]

    for _ in range(40):
        poll = client.get(f"/v1/runs/{run_id}")
        assert poll.status_code == 200
        body = poll.json()
        if body["status"] in ("done", "failed"):
            if body["status"] == "failed":
                pytest.fail(body.get("error") or "run failed")
            assert body["result"] is not None
            return
        time.sleep(0.25)

    pytest.fail(f"Run {run_id} did not complete in time")
