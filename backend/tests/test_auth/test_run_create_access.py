"""OIDC-enabled run creation — API keys for deployed runs, JWT for test runs."""

from __future__ import annotations

import pytest

from audit_workbench.db.seed import SEED_API_KEY
from audit_workbench.settings import clear_settings_cache
from tests.helpers.oidc_tokens import TEST_ISSUER, jwks_json_for_tests, mint_access_token


@pytest.fixture(autouse=True)
def _oidc_enabled(monkeypatch: pytest.MonkeyPatch):
    clear_settings_cache()
    monkeypatch.setenv("AUDIT_OIDC_ENABLED", "true")
    monkeypatch.setenv("AUDIT_OIDC_ISSUER", TEST_ISSUER)
    monkeypatch.setenv("AUDIT_OIDC_JWKS_JSON", jwks_json_for_tests())
    yield
    clear_settings_cache()


@pytest.mark.asyncio
async def test_deployed_run_rejects_missing_api_key(client):
    """Production POST /runs must not require platform JWT — only the workflow key."""
    unauthorized = await client.post("/v1/workflows/wf-invoice-audit/runs")
    assert unauthorized.status_code == 401


@pytest.mark.live
@pytest.mark.asyncio
async def test_deployed_run_accepts_workflow_api_key(live_client):
    ok = await live_client.post(
        "/v1/workflows/wf-invoice-audit/runs",
        headers={"Authorization": f"Bearer {SEED_API_KEY}"},
    )
    assert ok.status_code == 202
    assert ok.json()["runId"]


@pytest.mark.live
@pytest.mark.asyncio
async def test_deployed_run_json_accepts_workflow_api_key(live_client):
    ok = await live_client.post(
        "/v1/workflows/wf-invoice-audit/runs/json",
        headers={"Authorization": f"Bearer {SEED_API_KEY}"},
        json={"fileBindings": []},
    )
    assert ok.status_code == 202
    assert ok.json()["runId"]


@pytest.mark.asyncio
async def test_test_run_requires_platform_jwt(client):
    """Test-mode runs still require an operator JWT when OIDC is enabled."""
    no_jwt = await client.post(
        "/v1/workflows/wf-invoice-audit/runs/json",
        json={"snapshot": {"documents": [], "rules": []}},
    )
    assert no_jwt.status_code == 401

    viewer = mint_access_token(roles=["viewer"])
    forbidden = await client.post(
        "/v1/workflows/wf-invoice-audit/runs/json",
        json={"snapshot": {"documents": [], "rules": []}},
        headers={"Authorization": f"Bearer {viewer}"},
    )
    assert forbidden.status_code == 403


@pytest.mark.live
@pytest.mark.asyncio
async def test_test_run_accepts_operator_jwt(live_client):
    health = await live_client.get("/v1/healthz")
    if not health.json().get("oidcEnabled"):
        pytest.skip("OIDC not enabled on target stack")
    operator = mint_access_token(roles=["operator"])
    ok = await live_client.post(
        "/v1/workflows/wf-invoice-audit/runs/json",
        json={"snapshot": {"documents": [], "rules": []}},
        headers={"Authorization": f"Bearer {operator}"},
    )
    assert ok.status_code == 202
    assert ok.json()["runId"]
