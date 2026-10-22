"""User management use cases backed by the Keycloak admin API."""

from __future__ import annotations

from typing import Any

from repody.infra.auth import keycloak_admin as keycloak
from repody.infra.auth.principal import APP_REALM_ROLES, Principal
from repody.runtime.contracts.result import AppError, ErrorCode, Result
from repody.schemas.iam import (
    CreateIamUserRequest,
    IamUser,
    IamUsersResponse,
    UpdateIamUserRequest,
)
from repody.settings import Settings, get_settings

_DEV_USER = IamUser(
    id="dev-local",
    username="dev@local",
    email="dev@local",
    first_name="Dev",
    last_name="Admin",
    enabled=True,
    roles=["platform_admin"],
)


def _bad_request(message: str) -> AppError:
    return AppError(code=ErrorCode.BAD_REQUEST, message=message)


def _management_disabled(settings: Settings) -> AppError | None:
    if settings.oidc_enabled:
        return None
    return AppError(code=ErrorCode.INFRA, message="User management requires OIDC/Keycloak.")


def _invalid_roles(roles: list[str]) -> AppError | None:
    if not roles:
        return _bad_request("At least one application role is required.")
    invalid = [role for role in roles if role not in APP_REALM_ROLES]
    if invalid:
        return _bad_request(f"Invalid roles: {', '.join(invalid)}")
    return None


def _to_iam_user(raw: dict[str, Any], realm_roles: list[dict[str, Any]]) -> IamUser:
    role_names = [str(role["name"]) for role in realm_roles if role.get("name")]
    return IamUser(
        id=str(raw.get("id") or ""),
        username=str(raw.get("username") or ""),
        email=raw.get("email"),
        first_name=raw.get("firstName"),
        last_name=raw.get("lastName"),
        enabled=bool(raw.get("enabled", True)),
        roles=sorted(role for role in role_names if role in APP_REALM_ROLES),
    )


async def _find_raw_user(
    user_id: str, *, search: str | None, settings: Settings
) -> Result[dict[str, Any] | None]:
    users_r = await keycloak.list_users(search=search, settings=settings)
    if users_r.error:
        return Result.fail(users_r.error)
    return Result.ok(next((u for u in users_r.unwrap() if str(u.get("id")) == user_id), None))


async def _load_iam_user(raw: dict[str, Any], settings: Settings) -> Result[IamUser]:
    roles_r = await keycloak.user_realm_roles(str(raw.get("id") or ""), settings=settings)
    if roles_r.error:
        return Result.fail(roles_r.error)
    return Result.ok(_to_iam_user(raw, roles_r.unwrap()))


async def list_users(search: str | None) -> IamUsersResponse:
    """List users; management problems are reported in the response, never raised."""
    settings = get_settings()
    if not settings.oidc_enabled:
        return IamUsersResponse(
            users=[_DEV_USER],
            management_available=False,
            management_error="OIDC is disabled — dev mode uses a synthetic platform_admin principal.",
        )
    if not keycloak.keycloak_admin_configured(settings):
        return IamUsersResponse(
            users=[],
            management_available=False,
            management_error="Keycloak admin API is not configured on the API service.",
        )

    raw_users_r = await keycloak.list_users(search=search, settings=settings)
    if raw_users_r.error:
        return IamUsersResponse(
            users=[], management_available=False, management_error=raw_users_r.error.message
        )

    users: list[IamUser] = []
    for raw in raw_users_r.unwrap():
        if not raw.get("id"):
            continue
        user_r = await _load_iam_user(raw, settings)
        if user_r.error:
            return IamUsersResponse(
                users=[], management_available=False, management_error=user_r.error.message
            )
        users.append(user_r.unwrap())
    users.sort(key=lambda user: (user.email or user.username).lower())
    return IamUsersResponse(users=users, management_available=True)


async def create_user(body: CreateIamUserRequest) -> Result[IamUser]:
    settings = get_settings()
    if error := _management_disabled(settings) or _invalid_roles(body.roles):
        return Result.fail(error)

    username = body.email.strip().lower()
    payload = {
        "username": username,
        "email": username,
        "emailVerified": True,
        "enabled": body.enabled,
        "firstName": body.first_name.strip() or None,
        "lastName": body.last_name.strip() or None,
        "requiredActions": [],
    }
    user_id_r = await keycloak.create_user(payload, settings=settings)
    if user_id_r.error:
        return Result.fail(user_id_r.error)
    user_id = user_id_r.unwrap()

    for step in (
        keycloak.reset_password(user_id, body.password, temporary=False, settings=settings),
        keycloak.set_user_app_roles(user_id, body.roles, settings=settings),
    ):
        step_r = await step
        if step_r.error:
            return Result.fail(step_r.error)

    raw_r = await _find_raw_user(user_id, search=username, settings=settings)
    if raw_r.error:
        return Result.fail(raw_r.error)
    raw = raw_r.unwrap() or {"id": user_id, **payload}
    return await _load_iam_user(raw, settings)


def _self_edit_error(
    user_id: str, body: UpdateIamUserRequest, principal: Principal
) -> AppError | None:
    if user_id != principal.subject:
        return None
    if body.enabled is False:
        return _bad_request("You cannot disable your own account.")
    removes_own_admin = (
        body.roles is not None
        and "platform_admin" not in body.roles
        and "platform_admin" in principal.roles
    )
    if removes_own_admin:
        return _bad_request("You cannot remove your own platform_admin role.")
    return None


async def update_user(
    user_id: str, body: UpdateIamUserRequest, principal: Principal
) -> Result[IamUser]:
    settings = get_settings()
    if error := _management_disabled(settings) or _self_edit_error(user_id, body, principal):
        return Result.fail(error)
    if body.roles is not None and (error := _invalid_roles(body.roles)):
        return Result.fail(error)

    raw_r = await _find_raw_user(user_id, search=None, settings=settings)
    if raw_r.error:
        return Result.fail(raw_r.error)
    raw = raw_r.unwrap()
    if not raw:
        return Result.fail(AppError(code=ErrorCode.NOT_FOUND, message="User not found."))

    update_payload = {
        "username": raw.get("username"),
        "email": raw.get("email"),
        "emailVerified": raw.get("emailVerified", True),
        "enabled": body.enabled if body.enabled is not None else raw.get("enabled", True),
        "firstName": body.first_name if body.first_name is not None else raw.get("firstName"),
        "lastName": body.last_name if body.last_name is not None else raw.get("lastName"),
    }
    updated_r = await keycloak.update_user(user_id, update_payload, settings=settings)
    if updated_r.error:
        return Result.fail(updated_r.error)

    if body.password:
        password_r = await keycloak.reset_password(
            user_id, body.password, temporary=False, settings=settings
        )
        if password_r.error:
            return Result.fail(password_r.error)
    if body.roles is not None:
        roles_r = await keycloak.set_user_app_roles(user_id, body.roles, settings=settings)
        if roles_r.error:
            return Result.fail(roles_r.error)

    latest_r = await _find_raw_user(
        user_id, search=str(raw.get("username") or ""), settings=settings
    )
    if latest_r.error:
        return Result.fail(latest_r.error)
    return await _load_iam_user(latest_r.unwrap() or raw, settings)
