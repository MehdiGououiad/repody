"""Keycloak password-grant token for in-process operator benchmark jobs."""

from __future__ import annotations

from audit_workbench.auth.keycloak_token import fetch_password_grant_token
from audit_workbench.settings import get_settings


async def fetch_operator_benchmark_bearer_token() -> str | None:
    settings = get_settings()
    if not settings.oidc_enabled:
        return None
    if settings.operator_benchmark_bearer_token:
        return settings.operator_benchmark_bearer_token

    user = settings.operator_benchmark_user
    password = settings.operator_benchmark_password
    client_id = settings.keycloak_oauth_client_id
    client_secret = settings.keycloak_oauth_client_secret
    if not all([user, password, client_id, client_secret]):
        return None

    base = (settings.keycloak_admin_url or "http://keycloak:8080").rstrip("/")
    token_url = f"{base}/realms/{settings.keycloak_realm}/protocol/openid-connect/token"
    return await fetch_password_grant_token(
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        username=user,
        password=password,
    )
