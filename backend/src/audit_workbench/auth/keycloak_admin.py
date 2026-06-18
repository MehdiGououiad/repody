"""Keycloak Admin REST client for realm user management."""

from __future__ import annotations

import time
from typing import Any

import httpx
import structlog

from audit_workbench.auth.principal import APP_REALM_ROLES
from audit_workbench.settings import Settings, get_settings

log = structlog.get_logger(__name__)

_TOKEN_CACHE: dict[str, float | str] = {"token": "", "expires_at": 0.0}


class KeycloakAdminError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class KeycloakAdminClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        base = (self._settings.keycloak_admin_url or "").rstrip("/")
        if not base and self._settings.oidc_issuer:
            base = self._settings.oidc_issuer.split("/realms/")[0]
        self._base = base
        self._realm = self._settings.keycloak_realm
        self._user = self._settings.keycloak_admin_user
        self._password = self._settings.keycloak_admin_password

    @property
    def configured(self) -> bool:
        return bool(self._base and self._user and self._password)

    async def _admin_token(self) -> str:
        if not self.configured:
            raise KeycloakAdminError("Keycloak admin API is not configured.")
        now = time.time()
        cached = _TOKEN_CACHE.get("token")
        expires = float(_TOKEN_CACHE.get("expires_at") or 0)
        if isinstance(cached, str) and cached and now < expires - 30:
            return cached

        token_url = f"{self._base}/realms/master/protocol/openid-connect/token"
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "password",
                    "client_id": "admin-cli",
                    "username": self._user,
                    "password": self._password,
                },
            )
        if response.status_code >= 400:
            raise KeycloakAdminError(
                f"Keycloak admin login failed ({response.status_code}).",
                status_code=response.status_code,
            )
        payload = response.json()
        token = str(payload.get("access_token") or "")
        if not token:
            raise KeycloakAdminError("Keycloak admin login returned no access token.")
        ttl = int(payload.get("expires_in") or 60)
        _TOKEN_CACHE["token"] = token
        _TOKEN_CACHE["expires_at"] = now + ttl
        return token

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> httpx.Response:
        token = await self._admin_token()
        url = f"{self._base}/admin/realms/{self._realm}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                url,
                headers={"Authorization": f"Bearer {token}"},
                params=params,
                json=json,
            )
        if response.status_code >= 400:
            detail = response.text.strip()[:240] or response.reason_phrase
            raise KeycloakAdminError(
                f"Keycloak admin {method} {path} failed ({response.status_code}): {detail}",
                status_code=response.status_code,
            )
        return response

    async def list_users(self, *, search: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"max": 250}
        if search:
            params["search"] = search
        response = await self._request("GET", "/users", params=params)
        return response.json()

    async def create_user(self, payload: dict[str, Any]) -> str:
        response = await self._request("POST", "/users", json=payload)
        location = response.headers.get("location") or ""
        user_id = location.rstrip("/").split("/")[-1]
        if not user_id:
            raise KeycloakAdminError("Keycloak did not return a user id after create.")
        return user_id

    async def update_user(self, user_id: str, payload: dict[str, Any]) -> None:
        await self._request("PUT", f"/users/{user_id}", json=payload)

    async def reset_password(self, user_id: str, password: str, *, temporary: bool = False) -> None:
        await self._request(
            "PUT",
            f"/users/{user_id}/reset-password",
            json={"type": "password", "value": password, "temporary": temporary},
        )

    async def list_realm_roles(self) -> list[dict[str, Any]]:
        response = await self._request("GET", "/roles")
        return response.json()

    async def user_realm_roles(self, user_id: str) -> list[dict[str, Any]]:
        response = await self._request("GET", f"/users/{user_id}/role-mappings/realm")
        payload = response.json()
        roles = payload if isinstance(payload, list) else payload.get("realmMappings") or []
        return [role for role in roles if role.get("name") in APP_REALM_ROLES]

    async def set_user_app_roles(self, user_id: str, role_names: list[str]) -> None:
        invalid = [name for name in role_names if name not in APP_REALM_ROLES]
        if invalid:
            raise KeycloakAdminError(f"Invalid realm roles: {', '.join(invalid)}")

        all_roles = await self.list_realm_roles()
        by_name = {role["name"]: role for role in all_roles if role.get("name") in APP_REALM_ROLES}
        missing = [name for name in role_names if name not in by_name]
        if missing:
            raise KeycloakAdminError(f"Realm roles not found in Keycloak: {', '.join(missing)}")

        current = await self.user_realm_roles(user_id)
        current_names = {role["name"] for role in current}
        target_names = set(role_names)

        to_remove = [by_name[name] for name in current_names - target_names]
        to_add = [by_name[name] for name in target_names - current_names]

        if to_remove:
            await self._request(
                "DELETE",
                f"/users/{user_id}/role-mappings/realm",
                json=to_remove,
            )
        if to_add:
            await self._request(
                "POST",
                f"/users/{user_id}/role-mappings/realm",
                json=to_add,
            )


def keycloak_console_url(settings: Settings | None = None) -> str | None:
    cfg = settings or get_settings()
    if cfg.keycloak_admin_console_url:
        return cfg.keycloak_admin_console_url
    if cfg.oidc_issuer:
        return f"{cfg.oidc_issuer.split('/realms/')[0]}/admin"
    return None
