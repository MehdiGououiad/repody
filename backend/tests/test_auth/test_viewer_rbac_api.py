"""Casbin enforcement on real API routes when OIDC is enabled."""

from __future__ import annotations

import pytest

from audit_workbench.settings import clear_settings_cache
from tests.helpers.oidc_tokens import TEST_ISSUER, jwks_json_for_tests, mint_access_token


@pytest.fixture(autouse=True)
def _oidc_enabled(monkeypatch: pytest.MonkeyPatch):
    clear_settings_cache()
    monkeypatch.setenv("AUDIT_OIDC_ENABLED", "true")
    monkeypatch.setenv("AUDIT_OIDC_ISSUER", TEST_ISSUER)
    monkeypatch.setenv("AUDIT_OIDC_JWKS_JSON", jwks_json_for_tests())
    monkeypatch.setenv("AUDIT_OIDC_JWKS_URL", "")
    monkeypatch.setenv("AUDIT_OIDC_AUDIENCE", "")
    yield
    clear_settings_cache()


@pytest.mark.asyncio
async def test_viewer_cannot_read_metrics(client):
    viewer = mint_access_token(roles=["viewer"])
    res = await client.get("/v1/metrics", headers={"Authorization": f"Bearer {viewer}"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_operator_cannot_read_metrics(client):
    operator = mint_access_token(roles=["operator"])
    res = await client.get("/v1/metrics", headers={"Authorization": f"Bearer {operator}"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_read_metrics(client):
    admin = mint_access_token(roles=["admin"])
    res = await client.get("/v1/metrics", headers={"Authorization": f"Bearer {admin}"})
    assert res.status_code == 200
