"""Keycloak's Admin REST API, as the ``repody-admin`` service account (client credentials).

That account holds only realm-management's ``manage-users``, ``view-users``, ``query-users`` and
``query-groups``: it manages users and groups, never realm settings or clients. ``manage-users``
lets it map any realm role, ``platform_admin`` included: ``set_role`` gives only the roles Repody
manages, and its secret (KEYCLOAK_ADMIN_CLIENT_SECRET) is worth a platform admin's. Passwords are
temporary ones Keycloak makes the user replace at the first sign-in.
https://www.keycloak.org/docs-api/latest/rest-api/index.html
"""

import asyncio
import time
from dataclasses import dataclass
from functools import cache
from typing import Any

import httpx
import structlog

from repody.settings import get_settings

log = structlog.get_logger(__name__)

TIMEOUT_SECONDS = 10
TOKEN_MARGIN_SECONDS = 30  # refresh a little before Keycloak says the token expires


class KeycloakError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


@dataclass(frozen=True, slots=True)
class KcGroup:
    id: str
    name: str


@dataclass(frozen=True, slots=True)
class KcUser:
    id: str
    email: str
    first_name: str
    last_name: str
    enabled: bool
    created_ms: int
    realm_roles: frozenset[str]


def enabled() -> bool:
    return bool(get_settings().keycloak_admin_client_secret)


class KeycloakAdmin:
    def __init__(self) -> None:
        settings = get_settings()
        issuer = (settings.keycloak_internal_issuer or settings.oidc_issuer or "").rstrip("/")
        base, _, realm = issuer.rpartition("/realms/")
        self._token_url = f"{issuer}/protocol/openid-connect/token"
        self._admin_url = f"{base}/admin/realms/{realm}"
        self._client = httpx.AsyncClient(timeout=TIMEOUT_SECONDS)
        self._token: tuple[str, float] | None = None

    async def _access_token(self) -> str:
        if self._token and self._token[1] > time.monotonic():
            return self._token[0]
        settings = get_settings()
        secret = settings.keycloak_admin_client_secret
        response = await self._client.post(
            self._token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.keycloak_admin_client_id,
                "client_secret": secret.get_secret_value() if secret else "",
            },
        )
        if response.status_code != 200:
            log.error("keycloak_admin_token_failed", status=response.status_code)
            raise KeycloakError(502, "Keycloak refused Repody's admin account.")
        body = response.json()
        expires = time.monotonic() + int(body.get("expires_in", 60)) - TOKEN_MARGIN_SECONDS
        self._token = (body["access_token"], expires)
        return self._token[0]

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            token = await self._access_token()
            response = await self._client.request(
                method,
                f"{self._admin_url}{path}",
                headers={"Authorization": f"Bearer {token}"},
                **kwargs,
            )
        except httpx.HTTPError as exc:
            log.error("keycloak_admin_unreachable", path=path, error=repr(exc))
            raise KeycloakError(502, "Keycloak did not answer; try again shortly.") from exc
        if response.status_code == 409:
            raise KeycloakError(409, "It already exists in Keycloak.")
        if response.status_code == 404:
            raise KeycloakError(404, "Not found in Keycloak.")
        if response.status_code >= 400:
            log.error(
                "keycloak_admin_failed", method=method, path=path, status=response.status_code
            )
            raise KeycloakError(502, f"Keycloak answered {response.status_code}.")
        return response

    async def groups(self, prefix: str) -> list[KcGroup]:
        response = await self._request(
            "GET", "/groups", params={"search": prefix, "briefRepresentation": "true", "max": 1000}
        )
        return [
            KcGroup(id=g["id"], name=g["name"])
            for g in response.json()
            if str(g.get("name", "")).startswith(prefix)
        ]

    async def group(self, name: str) -> KcGroup | None:
        response = await self._request(
            "GET",
            "/groups",
            params={"search": name, "exact": "true", "briefRepresentation": "true"},
        )
        return next(
            (KcGroup(id=g["id"], name=g["name"]) for g in response.json() if g["name"] == name),
            None,
        )

    async def create_group(self, name: str) -> KcGroup:
        await self._request("POST", "/groups", json={"name": name})
        group = await self.group(name)
        if group is None:
            raise KeycloakError(502, "Keycloak did not create the group.")
        return group

    async def _roles(self, user_id: str) -> frozenset[str]:
        response = await self._request("GET", f"/users/{user_id}/role-mappings/realm")
        return frozenset(role["name"] for role in response.json())

    def _user(self, body: dict[str, Any], roles: frozenset[str]) -> KcUser:
        return KcUser(
            id=body["id"],
            email=body.get("email") or body.get("username", ""),
            first_name=body.get("firstName", ""),
            last_name=body.get("lastName", ""),
            enabled=bool(body.get("enabled", True)),
            created_ms=int(body.get("createdTimestamp", 0)),
            realm_roles=roles,
        )

    async def members(self, group_id: str, *, roles: bool = True) -> list[KcUser]:
        """The group's users, with their realm roles (one request per user, sent together), or
        without them (``roles=False``: counts and states only)."""
        response = await self._request(
            "GET",
            f"/groups/{group_id}/members",
            params={"briefRepresentation": "false", "max": 500},
        )
        bodies = response.json()
        found = await asyncio.gather(*(self._roles(b["id"]) for b in bodies)) if roles else []
        return [
            self._user(body, found[i] if roles else frozenset()) for i, body in enumerate(bodies)
        ]

    async def user(self, user_id: str) -> KcUser:
        response = await self._request("GET", f"/users/{user_id}")
        return self._user(response.json(), await self._roles(user_id))

    async def user_groups(self, user_id: str) -> list[KcGroup]:
        response = await self._request("GET", f"/users/{user_id}/groups")
        return [KcGroup(id=g["id"], name=g["name"]) for g in response.json()]

    async def find_user(self, email: str) -> KcUser | None:
        response = await self._request(
            "GET", "/users", params={"email": email, "exact": "true", "briefRepresentation": "true"}
        )
        found = [u for u in response.json() if (u.get("email") or "").lower() == email.lower()]
        return await self.user(found[0]["id"]) if found else None

    async def create_user(self, *, email: str, first_name: str, last_name: str) -> str:
        response = await self._request(
            "POST",
            "/users",
            json={
                "username": email,
                "email": email,
                "firstName": first_name,
                "lastName": last_name,
                "enabled": True,
                "emailVerified": True,
                "requiredActions": ["UPDATE_PASSWORD"],
            },
        )
        return response.headers["Location"].rstrip("/").rsplit("/", 1)[-1]

    async def set_temporary_password(self, user_id: str, password: str) -> None:
        await self._request(
            "PUT",
            f"/users/{user_id}/reset-password",
            json={"type": "password", "value": password, "temporary": True},
        )

    async def set_enabled(self, user_id: str, enabled: bool) -> None:
        await self._request("PUT", f"/users/{user_id}", json={"enabled": enabled})

    async def join(self, user_id: str, group_id: str) -> None:
        await self._request("PUT", f"/users/{user_id}/groups/{group_id}")

    async def leave(self, user_id: str, group_id: str) -> None:
        await self._request("DELETE", f"/users/{user_id}/groups/{group_id}")

    async def set_role(self, user_id: str, role: str, managed: frozenset[str]) -> None:
        """Give the user ``role`` and none of the other ``managed`` realm roles. Only a managed
        role is given: Keycloak itself would let this account grant any realm role."""
        if role not in managed:
            raise KeycloakError(403, f"Repody does not give the role {role}.")
        current = await self._request("GET", f"/users/{user_id}/role-mappings/realm")
        stale = [
            {"id": r["id"], "name": r["name"]}
            for r in current.json()
            if r["name"] in managed and r["name"] != role
        ]
        if stale:
            await self._request("DELETE", f"/users/{user_id}/role-mappings/realm", json=stale)
        if any(r["name"] == role for r in current.json()):
            return
        # The roles this account may give the user: reading a role by name needs view-realm.
        available = await self._request("GET", f"/users/{user_id}/role-mappings/realm/available")
        match = next((r for r in available.json() if r["name"] == role), None)
        if match is None:
            raise KeycloakError(403, f"Keycloak does not let Repody give the role {role}.")
        await self._request(
            "POST",
            f"/users/{user_id}/role-mappings/realm",
            json=[{"id": match["id"], "name": match["name"]}],
        )

    async def close(self) -> None:
        await self._client.aclose()


@cache
def keycloak_admin() -> KeycloakAdmin:
    return KeycloakAdmin()
