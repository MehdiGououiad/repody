"""Keycloak Admin REST — plain async functions returning Result."""

from __future__ import annotations

import time
from typing import Any

import httpx
import structlog

from repody.infra.auth.principal import APP_REALM_ROLES
from repody.infra.http import get_http_client
from repody.runtime.contracts.result import AppError, ErrorCode, Result
from repody.settings import Settings, get_settings

log = structlog.get_logger(__name__)

_TOKEN_CACHE: dict[str, float | str] = {"token": "", "expires_at": 0.0}


def _admin_base(settings: Settings) -> tuple[str, str, str, str]:
    base = (settings.keycloak_admin_url or "").rstrip("/")
    if not base and settings.oidc_issuer:
        base = settings.oidc_issuer.split("/realms/")[0]
    return (
        base,
        settings.keycloak_realm,
        settings.keycloak_admin_user,
        settings.keycloak_admin_password,
    )


def keycloak_admin_configured(settings: Settings | None = None) -> bool:
    cfg = settings or get_settings()
    base, _realm, user, password = _admin_base(cfg)
    return bool(base and user and password)


def keycloak_console_url(settings: Settings | None = None) -> str | None:
    cfg = settings or get_settings()
    if cfg.keycloak_admin_console_url:
        return cfg.keycloak_admin_console_url
    if cfg.oidc_issuer:
        return f"{cfg.oidc_issuer.split('/realms/')[0]}/admin"
    return None


def _admin_error(message: str, *, status_code: int | None = None) -> AppError:
    return AppError(
        code=ErrorCode.INFRA if (status_code or 500) >= 500 else ErrorCode.VALIDATION,
        message=message,
        cause=str(status_code) if status_code is not None else None,
    )


async def _admin_token(settings: Settings) -> Result[str]:
    base, _realm, user, password = _admin_base(settings)
    if not (base and user and password):
        return Result.fail(_admin_error("Keycloak admin API is not configured."))

    now = time.time()
    cached = _TOKEN_CACHE.get("token")
    expires = float(_TOKEN_CACHE.get("expires_at") or 0)
    if isinstance(cached, str) and cached and now < expires - 30:
        return Result.ok(cached)

    token_url = f"{base}/realms/master/protocol/openid-connect/token"
    client = get_http_client()
    response = await client.post(
        token_url,
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": user,
            "password": password,
        },
        timeout=20.0,
    )
    if response.status_code >= 400:
        return Result.fail(
            _admin_error(
                f"Keycloak admin login failed ({response.status_code}).",
                status_code=response.status_code,
            )
        )
    payload = response.json()
    token = str(payload.get("access_token") or "")
    if not token:
        return Result.fail(_admin_error("Keycloak admin login returned no access token."))
    ttl = int(payload.get("expires_in") or 60)
    _TOKEN_CACHE["token"] = token
    _TOKEN_CACHE["expires_at"] = now + ttl
    return Result.ok(token)


async def _admin_request(
    settings: Settings,
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json: Any = None,
) -> Result[httpx.Response]:
    token_r = await _admin_token(settings)
    if not token_r.is_ok:
        return Result.fail(token_r.error or _admin_error("Admin token failed"))
    base, realm, _user, _password = _admin_base(settings)
    url = f"{base}/admin/realms/{realm}{path}"
    client = get_http_client()
    response = await client.request(
        method,
        url,
        headers={"Authorization": f"Bearer {token_r.unwrap()}"},
        params=params,
        json=json,
        timeout=30.0,
    )
    if response.status_code >= 400:
        detail = response.text.strip()[:240] or response.reason_phrase
        return Result.fail(
            _admin_error(
                f"Keycloak admin {method} {path} failed ({response.status_code}): {detail}",
                status_code=response.status_code,
            )
        )
    return Result.ok(response)


async def list_users(
    *,
    search: str | None = None,
    settings: Settings | None = None,
) -> Result[list[dict[str, Any]]]:
    cfg = settings or get_settings()
    params: dict[str, Any] = {"max": 250}
    if search:
        params["search"] = search
    response = await _admin_request(cfg, "GET", "/users", params=params)
    if not response.is_ok:
        return Result.fail(response.error or _admin_error("list_users failed"))
    return Result.ok(response.unwrap().json())


async def create_user(
    payload: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> Result[str]:
    cfg = settings or get_settings()
    response = await _admin_request(cfg, "POST", "/users", json=payload)
    if not response.is_ok:
        return Result.fail(response.error or _admin_error("create_user failed"))
    location = response.unwrap().headers.get("location") or ""
    user_id = location.rstrip("/").split("/")[-1]
    if not user_id:
        return Result.fail(_admin_error("Keycloak did not return a user id after create."))
    return Result.ok(user_id)


async def update_user(
    user_id: str,
    payload: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> Result[None]:
    cfg = settings or get_settings()
    response = await _admin_request(cfg, "PUT", f"/users/{user_id}", json=payload)
    if not response.is_ok:
        return Result.fail(response.error or _admin_error("update_user failed"))
    return Result.ok(None)


async def reset_password(
    user_id: str,
    password: str,
    *,
    temporary: bool = False,
    settings: Settings | None = None,
) -> Result[None]:
    cfg = settings or get_settings()
    response = await _admin_request(
        cfg,
        "PUT",
        f"/users/{user_id}/reset-password",
        json={"type": "password", "value": password, "temporary": temporary},
    )
    if not response.is_ok:
        return Result.fail(response.error or _admin_error("reset_password failed"))
    return Result.ok(None)


async def list_realm_roles(*, settings: Settings | None = None) -> Result[list[dict[str, Any]]]:
    cfg = settings or get_settings()
    response = await _admin_request(cfg, "GET", "/roles")
    if not response.is_ok:
        return Result.fail(response.error or _admin_error("list_realm_roles failed"))
    return Result.ok(response.unwrap().json())


async def user_realm_roles(
    user_id: str,
    *,
    settings: Settings | None = None,
) -> Result[list[dict[str, Any]]]:
    cfg = settings or get_settings()
    response = await _admin_request(cfg, "GET", f"/users/{user_id}/role-mappings/realm")
    if not response.is_ok:
        return Result.fail(response.error or _admin_error("user_realm_roles failed"))
    payload = response.unwrap().json()
    roles = payload if isinstance(payload, list) else payload.get("realmMappings") or []
    return Result.ok([role for role in roles if role.get("name") in APP_REALM_ROLES])


async def set_user_app_roles(
    user_id: str,
    role_names: list[str],
    *,
    settings: Settings | None = None,
) -> Result[None]:
    cfg = settings or get_settings()
    invalid = [name for name in role_names if name not in APP_REALM_ROLES]
    if invalid:
        return Result.fail(_admin_error(f"Invalid realm roles: {', '.join(invalid)}"))

    all_roles_r = await list_realm_roles(settings=cfg)
    if not all_roles_r.is_ok:
        return Result.fail(all_roles_r.error or _admin_error("list_realm_roles failed"))
    by_name = {
        role["name"]: role for role in all_roles_r.unwrap() if role.get("name") in APP_REALM_ROLES
    }
    missing = [name for name in role_names if name not in by_name]
    if missing:
        return Result.fail(_admin_error(f"Realm roles not found in Keycloak: {', '.join(missing)}"))

    current_r = await user_realm_roles(user_id, settings=cfg)
    if not current_r.is_ok:
        return Result.fail(current_r.error or _admin_error("user_realm_roles failed"))
    current_names = {role["name"] for role in current_r.unwrap()}
    target_names = set(role_names)

    to_remove = [by_name[name] for name in current_names - target_names]
    to_add = [by_name[name] for name in target_names - current_names]

    if to_remove:
        removed = await _admin_request(
            cfg,
            "DELETE",
            f"/users/{user_id}/role-mappings/realm",
            json=to_remove,
        )
        if not removed.is_ok:
            return Result.fail(removed.error or _admin_error("remove roles failed"))
    if to_add:
        added = await _admin_request(
            cfg,
            "POST",
            f"/users/{user_id}/role-mappings/realm",
            json=to_add,
        )
        if not added.is_ok:
            return Result.fail(added.error or _admin_error("add roles failed"))
    return Result.ok(None)
