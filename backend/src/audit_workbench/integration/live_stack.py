"""Live stack helpers for integration tests and operator scripts."""

from __future__ import annotations

import os

import httpx

from audit_workbench.auth.keycloak_token import fetch_password_grant_token_sync

DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_AUTH_URL = "http://auth.repody.local"
DEFAULT_KEYCLOAK_USER = "operator@repody.local"
DEFAULT_KEYCLOAK_PASSWORD = "repody-dev"
DEFAULT_KEYCLOAK_CLIENT_ID = "repody-web"
DEFAULT_KEYCLOAK_CLIENT_SECRET = "repody-web-dev-secret"


def live_api_base() -> str:
    return os.environ.get("E2E_API_URL", DEFAULT_API_URL).rstrip("/")


def live_auth_url() -> str:
    return os.environ.get("E2E_AUTH_URL", DEFAULT_AUTH_URL).rstrip("/")


def fetch_keycloak_token() -> str:
    return fetch_password_grant_token_sync(
        token_url=f"{live_auth_url()}/realms/repody/protocol/openid-connect/token",
        client_id=os.environ.get("E2E_KEYCLOAK_CLIENT_ID", DEFAULT_KEYCLOAK_CLIENT_ID),
        client_secret=os.environ.get(
            "E2E_KEYCLOAK_CLIENT_SECRET", DEFAULT_KEYCLOAK_CLIENT_SECRET
        ),
        username=os.environ.get("E2E_KEYCLOAK_USER", DEFAULT_KEYCLOAK_USER),
        password=os.environ.get("E2E_KEYCLOAK_PASSWORD", DEFAULT_KEYCLOAK_PASSWORD),
    )


def live_health(client: httpx.Client | None = None) -> dict:
    if client is None:
        with httpx.Client(base_url=live_api_base(), timeout=10.0) as probe:
            response = probe.get("/v1/healthz")
            response.raise_for_status()
            return response.json()
    response = client.get("/v1/healthz")
    response.raise_for_status()
    return response.json()


def live_oidc_enabled(client: httpx.Client | None = None) -> bool:
    return bool(live_health(client).get("oidcEnabled"))


def live_inference_ready(client: httpx.Client | None = None) -> bool:
    health = live_health(client)
    return health.get("modelRunner") is True


def live_auth_headers() -> dict[str, str]:
    if not live_oidc_enabled():
        return {}
    return {"Authorization": f"Bearer {fetch_keycloak_token()}"}


def create_live_client(**kwargs) -> httpx.Client:
    headers = live_auth_headers()
    return httpx.Client(
        base_url=live_api_base(),
        headers=headers,
        timeout=kwargs.pop("timeout", 30.0),
        **kwargs,
    )


def create_anonymous_live_client(**kwargs) -> httpx.Client:
    return httpx.Client(
        base_url=live_api_base(),
        timeout=kwargs.pop("timeout", 30.0),
        **kwargs,
    )


def create_live_async_client(**kwargs) -> httpx.AsyncClient:
    headers = live_auth_headers()
    return httpx.AsyncClient(
        base_url=live_api_base(),
        headers=headers,
        timeout=kwargs.pop("timeout", httpx.Timeout(600.0)),
        **kwargs,
    )


def assert_metrics_access(response: httpx.Response, *, oidc_enabled: bool) -> None:
    if oidc_enabled:
        assert response.status_code == 403
    else:
        assert response.status_code == 200
        assert "kpis" in response.json()


def assert_settings_config_access(response: httpx.Response, *, oidc_enabled: bool) -> None:
    if oidc_enabled:
        assert response.status_code == 200
        cfg = response.json()
        assert cfg.get("maxUploadBytes", 0) > 0
        assert cfg.get("documentModels")
    else:
        assert response.status_code == 200
        assert response.json().get("maxUploadBytes", 0) > 0
