"""Keycloak password-grant token for live tests and smoke scripts (never used by the app)."""

from __future__ import annotations

import httpx


def fetch_password_grant_token_sync(
    *,
    token_url: str,
    client_id: str,
    client_secret: str,
    username: str,
    password: str,
    timeout: float = 15.0,
) -> str:
    response = httpx.post(
        token_url,
        data={
            "grant_type": "password",
            "client_id": client_id,
            "client_secret": client_secret,
            "username": username,
            "password": password,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["access_token"]
