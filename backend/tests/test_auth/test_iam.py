"""IAM API tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from audit_workbench.auth.keycloak_admin import KeycloakAdminClient
from audit_workbench.main import app
from audit_workbench.settings import clear_settings_cache


@pytest.mark.asyncio
async def test_iam_me_dev_principal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUDIT_OIDC_ENABLED", "false")
    clear_settings_cache()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/iam/me")
    assert response.status_code == 200
    payload = response.json()
    assert payload["subject"] == "dev-local"
    assert "platform_admin" in payload["roles"]
    assert payload["canManageUsers"] is True


@pytest.mark.asyncio
async def test_iam_catalog_lists_roles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUDIT_OIDC_ENABLED", "false")
    clear_settings_cache()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/iam/catalog")
    assert response.status_code == 200
    payload = response.json()
    role_ids = {role["id"] for role in payload["roles"]}
    assert role_ids == {"platform_admin", "admin", "operator", "viewer"}


@pytest.mark.asyncio
async def test_iam_users_list_dev_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUDIT_OIDC_ENABLED", "false")
    clear_settings_cache()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/iam/users")
    assert response.status_code == 200
    payload = response.json()
    assert payload["managementAvailable"] is False
    assert len(payload["users"]) == 1


@pytest.mark.asyncio
async def test_keycloak_user_realm_roles_accepts_keycloak_list_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        def json(self) -> list[dict[str, str]]:
            return [
                {"name": "platform_admin"},
                {"name": "default-roles-repody"},
                {"name": "viewer"},
            ]

    async def fake_request(
        self: KeycloakAdminClient,
        method: str,
        path: str,
        **kwargs: object,
    ) -> FakeResponse:
        assert method == "GET"
        assert path == "/users/user-1/role-mappings/realm"
        return FakeResponse()

    monkeypatch.setattr(KeycloakAdminClient, "_request", fake_request)

    roles = await KeycloakAdminClient().user_realm_roles("user-1")

    assert [role["name"] for role in roles] == ["platform_admin", "viewer"]
