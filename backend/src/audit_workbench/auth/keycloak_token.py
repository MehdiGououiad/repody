"""Unified Keycloak OAuth password-grant token fetch."""

from __future__ import annotations

import httpx


async def fetch_password_grant_token(
    *,
    token_url: str,
    client_id: str,
    client_secret: str,
    username: str,
    password: str,
    timeout: float = 15.0,
) -> str:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            token_url,
            data={
                "grant_type": "password",
                "client_id": client_id,
                "client_secret": client_secret,
                "username": username,
                "password": password,
            },
        )
    if response.is_error:
        raise RuntimeError(
            f"Keycloak token request failed ({response.status_code}): {response.text[:500]}"
        )
    payload = response.json()
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("Keycloak token response missing access_token")
    return token


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
    if response.is_error:
        raise RuntimeError(
            f"Keycloak token request failed ({response.status_code}): {response.text[:500]}"
        )
    payload = response.json()
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("Keycloak token response missing access_token")
    return token
