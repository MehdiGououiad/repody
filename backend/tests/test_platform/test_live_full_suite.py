"""Production-like live API suite — all public endpoints and extraction/validation paths.

Requires a running stack (Hatchet + workers + inference). Run via:
  pnpm test:platform:live
"""

from __future__ import annotations

import time
import uuid

import httpx
import pytest

from audit_workbench.db.seed import SEED_WORKFLOW_ID
from audit_workbench.extraction.model_registry import REPODY_VLM_CATALOG_ID
from tests.helpers.live_stack import (
    assert_metrics_access,
    assert_settings_config_access,
    create_anonymous_live_client,
    create_live_async_client,
    create_live_client,
    live_api_base,
    live_inference_ready,
    live_oidc_enabled,
)
from tests.test_e2e.facture_helpers import (
    EXPECTED_TOTAL,
    EXPECTED_TVA,
    FACTURE_PDF,
    FACTURE_UI_PATHS,
    LOGIC_RULE_TOTAL_FAIL,
    LOGIC_RULE_TOTAL_OK,
    LOGIC_RULE_TVA_UNDER_500,
    LOGIC_RULE_TVA_UNDER_500_UI_CONDITIONS,
    WORKFLOW_NAME,
    document_def,
    document_def_tva,
    facture_bytes,
    new_doc_id,
    rule_status_from_result,
    rules_for_case,
    total_from_result,
    tva_from_result,
)
from tests.test_e2e.ui_flow import run_test_with_files, save_workflow

BASE = live_api_base()
pytestmark = pytest.mark.live

requires_facture = pytest.mark.skipif(
    not FACTURE_PDF.is_file(),
    reason="Facture.pdf fixture missing",
)


@pytest.fixture(scope="module")
def client():
    with create_live_client(timeout=120.0) as c:
        yield c


@pytest.fixture(scope="module")
def oidc_enabled(client: httpx.Client) -> bool:
    return live_oidc_enabled(client)


@pytest.fixture(scope="module")
def require_inference(client: httpx.Client):
    if not live_inference_ready(client):
        pytest.skip("document-model inference not reachable (healthz modelRunner != true)")


@pytest.fixture
async def async_client():
    async with create_live_async_client(timeout=httpx.Timeout(1200.0, connect=30.0)) as client:
        yield client


# --- Platform surface ---


def test_live_health_and_config(client: httpx.Client, oidc_enabled: bool):
    live = client.get("/v1/healthz/live")
    assert live.status_code == 200
    assert live.json()["status"] == "ok"

    health = client.get("/v1/healthz")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "ok"
    assert body["queueBackend"] == "hatchet"
    assert body.get("hatchetConfigured") is True

    config = client.get("/v1/platform/config")
    assert_settings_config_access(config, oidc_enabled=oidc_enabled)
    if not oidc_enabled:
        cfg = config.json()
        assert cfg.get("maxUploadBytes", 0) > 0
        assert cfg.get("documentModels")


def test_live_models_catalog_and_rules(client: httpx.Client, oidc_enabled: bool):
    catalog = client.get("/v1/models/catalog")
    assert catalog.status_code == 200
    cat = catalog.json()
    path_ids = {p["id"] for p in cat["paths"]}
    assert "document_model" in path_ids
    assert cat["defaultPath"] == "document_model"
    val_ids = {v["id"] for v in cat["validationModes"]}
    assert "logic_only" in val_ids
    models = {m["id"]: m for m in cat["models"]}
    assert REPODY_VLM_CATALOG_ID in models

    rules = client.get("/v1/rules/library")
    assert rules.status_code == 200
    assert len(rules.json()["rules"]) >= 1

    metrics = client.get("/v1/metrics")
    assert_metrics_access(metrics, oidc_enabled=oidc_enabled)


def test_live_uploads_and_diagnostics(client: httpx.Client):
    caps = client.get("/v1/uploads/capabilities")
    assert caps.status_code == 200
    assert caps.json()["storageBackend"] in ("local", "s3")

    diag = client.get("/v1/diagnostics/ocr")
    assert diag.status_code == 200
    assert diag.json().get("ok") is True

    op = client.get("/v1/operator/status")
    assert op.status_code == 200
    assert "actionsEnabled" in op.json()


def _unique_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def _assert_workflow_exists(client: httpx.Client, wf_id: str) -> None:
    for _ in range(5):
        detail = client.get(f"/v1/workflows/{wf_id}")
        if detail.status_code == 200:
            assert detail.json()["workflow"]["id"] == wf_id
            return
        time.sleep(0.2)
    pytest.fail(f"Workflow {wf_id} not visible after PUT")


# --- Workflow CRUD + dry-run ---


def test_live_workflow_crud_deploy_and_dry_run(client: httpx.Client):
    wf_id = _unique_id("wf-live-full")
    doc_id = _unique_id("doc")
    field_id = _unique_id("f")

    created = client.put(
        f"/v1/workflows/{wf_id}",
        json={
            "id": wf_id,
            "name": "Live full suite",
            "description": "crud",
            "status": "draft",
            "owner": "live-e2e",
            "documents": [
                {
                    "id": doc_id,
                    "documentType": "Invoice",
                    "schema": [{"id": field_id, "name": "total_amount", "description": "Total"}],
                }
            ],
            "rules": [
                {
                    "id": _unique_id("rule"),
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
    assert created.status_code == 200
    _assert_workflow_exists(client, wf_id)

    dry = client.post(
        f"/v1/workflows/{wf_id}/dry-run",
        json={
            "fields": [
                {"id": field_id, "name": "total_amount", "description": "", "sampleValue": "100"}
            ],
            "rules": [
                {
                    "id": _unique_id("rule"),
                    "name": "Positive total",
                    "kind": "logic",
                    "body": "total_amount > 0",
                    "severity": "reject",
                }
            ],
        },
    )
    assert dry.status_code == 200
    assert dry.json()["ruleResults"][0]["status"] == "passed"

    deployed = client.post(f"/v1/workflows/{wf_id}/deploy", json={})
    assert deployed.status_code == 200
    api_key = deployed.json()["workflow"]["apiKey"]
    assert api_key

    with create_anonymous_live_client() as anon:
        unauthorized = anon.post(f"/v1/workflows/{wf_id}/runs")
        assert unauthorized.status_code == 401

        started = None
        for _ in range(5):
            started = anon.post(
                f"/v1/workflows/{wf_id}/runs",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if started.status_code == 202:
                break
            time.sleep(0.3)
    assert started is not None and started.status_code == 202
    run_id = started.json()["runId"]
    _poll_sync(client, run_id, timeout_s=120)


# --- Runs: json test path, status poll, SSE ---


def test_live_json_test_run_and_audit_detail(client: httpx.Client):
    started = client.post(
        f"/v1/workflows/{SEED_WORKFLOW_ID}/runs/json",
        json={
            "snapshot": {
                "documents": [],
                "rules": [],
                "workflowName": "Invoice Audit Pipeline",
            }
        },
    )
    assert started.status_code == 202
    run_id = started.json()["runId"]

    status = client.get(f"/v1/runs/{run_id}/status")
    assert status.status_code == 200
    assert status.json().get("progress") is not None or status.json()["status"] == "done"

    result = _poll_sync(client, run_id, timeout_s=120)
    audit_id = result["id"]
    detail = client.get(f"/v1/audits/{audit_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == audit_id


def test_live_run_events_sse(client: httpx.Client):
    started = client.post(
        f"/v1/workflows/{SEED_WORKFLOW_ID}/runs/json",
        json={
            "snapshot": {
                "documents": [],
                "rules": [],
                "workflowName": "Invoice Audit Pipeline",
            }
        },
    )
    assert started.status_code == 202
    run_id = started.json()["runId"]

    with client.stream("GET", f"/v1/runs/{run_id}/events", timeout=15.0) as stream:
        assert stream.status_code == 200
        chunk = b""
        for part in stream.iter_bytes():
            chunk += part
            if b"data:" in chunk or len(chunk) >= 64:
                break
        assert b"data:" in chunk


# --- Presigned upload + json run (production upload path) ---


@requires_facture
def test_live_presign_confirm_json_run(client: httpx.Client, require_inference):
    pdf = facture_bytes()
    case = FACTURE_UI_PATHS[0]
    doc_id = new_doc_id()
    wf_id = f"wf-presign-{uuid.uuid4().hex}"
    documents = [document_def(case, doc_id=doc_id)]
    rules = rules_for_case(case)

    assert (
        client.put(
            f"/v1/workflows/{wf_id}",
            json={
                "id": wf_id,
                "name": WORKFLOW_NAME,
                "description": "presign",
                "status": "draft",
                "owner": "live-e2e",
                "documents": documents,
                "rules": rules,
            },
        ).status_code
        == 200
    )

    presign = client.post(
        "/v1/uploads/presign",
        json={
            "files": [
                {
                    "fileName": "Facture.pdf",
                    "mimeType": "application/pdf",
                    "size": len(pdf),
                    "documentId": doc_id,
                }
            ]
        },
    )
    assert presign.status_code == 200
    item = presign.json()["uploads"][0]

    put = httpx.put(
        item["uploadUrl"],
        content=pdf,
        headers=item.get("headers") or {"Content-Type": "application/pdf"},
        timeout=120.0,
    )
    assert put.status_code in (200, 204)

    confirm = client.post("/v1/uploads/confirm", json={"storageKeys": [item["storageKey"]]})
    assert confirm.status_code == 200
    binding = confirm.json()["uploads"][0]

    started = client.post(
        f"/v1/workflows/{wf_id}/runs/json",
        json={
            "payload": {"documents": documents, "rules": rules, "workflowName": WORKFLOW_NAME},
            "fileBindings": [
                {
                    "documentId": doc_id,
                    "storageKey": binding["storageKey"],
                    "mimeType": binding["mimeType"],
                    "fileName": binding["fileName"],
                }
            ],
        },
    )
    assert started.status_code == 202
    result = _poll_sync(client, started.json()["runId"], timeout_s=900)
    assert total_from_result(result) == EXPECTED_TOTAL
    assert rule_status_from_result(result, rule_name=LOGIC_RULE_TOTAL_OK["name"]) == "passed"


# --- Multipart extraction + validation scenarios (UI Test tab parity) ---


@requires_facture
@pytest.mark.asyncio
async def test_live_multipart_extraction_logic_pass(
    async_client: httpx.AsyncClient, require_inference
):
    case = FACTURE_UI_PATHS[0]
    doc_id = new_doc_id()
    documents = [document_def(case, doc_id=doc_id)]
    rules = rules_for_case(case)
    wf_id = await save_workflow(
        async_client,
        wf_id=_unique_id("wf-live-mp-pass"),
        name=WORKFLOW_NAME,
        documents=documents,
        rules=rules,
    )
    pdf = facture_bytes()
    result = await run_test_with_files(
        async_client,
        wf_id,
        documents=documents,
        rules=rules,
        workflow_name=WORKFLOW_NAME,
        files_by_doc_id={doc_id: ("Facture.pdf", pdf, "application/pdf")},
        max_wait_ms=900_000,
    )
    assert total_from_result(result) == EXPECTED_TOTAL
    assert rule_status_from_result(result, rule_name=LOGIC_RULE_TOTAL_OK["name"]) == "passed"
    assert result["status"] == "passed"


@requires_facture
@pytest.mark.asyncio
async def test_live_multipart_extraction_logic_fail(
    async_client: httpx.AsyncClient, require_inference
):
    case = FACTURE_UI_PATHS[0]
    doc_id = new_doc_id()
    documents = [document_def(case, doc_id=doc_id)]
    rules = [LOGIC_RULE_TOTAL_FAIL]
    wf_id = await save_workflow(
        async_client,
        wf_id=_unique_id("wf-live-mp-fail"),
        name=WORKFLOW_NAME,
        documents=documents,
        rules=rules,
    )
    pdf = facture_bytes()
    result = await run_test_with_files(
        async_client,
        wf_id,
        documents=documents,
        rules=rules,
        workflow_name=WORKFLOW_NAME,
        files_by_doc_id={doc_id: ("Facture.pdf", pdf, "application/pdf")},
        max_wait_ms=900_000,
    )
    assert total_from_result(result) == EXPECTED_TOTAL
    assert rule_status_from_result(result, rule_name=LOGIC_RULE_TOTAL_FAIL["name"]) == "failed"
    assert result["status"] == "failed"


@requires_facture
@pytest.mark.asyncio
async def test_live_multipart_tva_validation_fail(
    async_client: httpx.AsyncClient, require_inference
):
    case = FACTURE_UI_PATHS[0]
    doc_id = new_doc_id()
    documents = [document_def_tva(case, doc_id=doc_id)]
    rules = [
        {**LOGIC_RULE_TVA_UNDER_500, "id": f"logic-{uuid.uuid4().hex[:6]}", "appliesTo": [doc_id]}
    ]
    wf_id = await save_workflow(
        async_client,
        wf_id=_unique_id("wf-live-tva"),
        name=WORKFLOW_NAME,
        documents=documents,
        rules=rules,
    )
    pdf = facture_bytes()
    result = await run_test_with_files(
        async_client,
        wf_id,
        documents=documents,
        rules=rules,
        workflow_name=WORKFLOW_NAME,
        files_by_doc_id={doc_id: ("Facture.pdf", pdf, "application/pdf")},
        max_wait_ms=900_000,
    )
    assert tva_from_result(result) == EXPECTED_TVA
    assert rule_status_from_result(result, rule_name=LOGIC_RULE_TVA_UNDER_500["name"]) == "failed"
    assert result["status"] == "failed"


@requires_facture
@pytest.mark.asyncio
async def test_live_multipart_ui_conditions_validation(
    async_client: httpx.AsyncClient, require_inference
):
    case = FACTURE_UI_PATHS[0]
    doc_id = new_doc_id()
    documents = [document_def_tva(case, doc_id=doc_id)]
    rules = [
        {
            **LOGIC_RULE_TVA_UNDER_500_UI_CONDITIONS,
            "id": f"logic-{uuid.uuid4().hex[:6]}",
            "appliesTo": [doc_id],
        }
    ]
    wf_id = await save_workflow(
        async_client,
        wf_id=_unique_id("wf-live-ui-cond"),
        name=WORKFLOW_NAME,
        documents=documents,
        rules=rules,
    )
    pdf = facture_bytes()
    result = await run_test_with_files(
        async_client,
        wf_id,
        documents=documents,
        rules=rules,
        workflow_name=WORKFLOW_NAME,
        files_by_doc_id={doc_id: ("Facture.pdf", pdf, "application/pdf")},
        max_wait_ms=900_000,
    )
    assert tva_from_result(result) == EXPECTED_TVA
    rule_results = result.get("ruleResults") or []
    assert any(r.get("status") == "failed" for r in rule_results), rule_results
    assert result["status"] == "failed"


def _poll_sync(client: httpx.Client, run_id: str, *, timeout_s: float = 120) -> dict:
    deadline = time.time() + timeout_s
    last_error = None
    while time.time() < deadline:
        poll = client.get(f"/v1/runs/{run_id}/status")
        poll.raise_for_status()
        body = poll.json()
        status = body.get("status")
        if status == "done":
            detail = client.get(f"/v1/runs/{run_id}")
            detail.raise_for_status()
            result = detail.json().get("result")
            assert result is not None, detail.json()
            return result
        if status == "failed":
            last_error = body.get("error") or "run failed"
            break
        time.sleep(1.0)
    pytest.fail(last_error or f"Run {run_id} timed out after {timeout_s}s")
