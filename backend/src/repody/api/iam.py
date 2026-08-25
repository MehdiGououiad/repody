"""Identity and access management â€” Casbin matrix + Keycloak user admin."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from repody.api.errors import raise_app_error
from repody.infra.auth import keycloak_admin as keycloak
from repody.infra.auth.casbin_authorizer import authorize
from repody.infra.auth.dependencies import get_current_principal, require_permission
from repody.infra.auth.principal import APP_REALM_ROLES, Principal
from repody.infra.auth.rbac_catalog import (
    ROLE_DESCRIPTIONS,
    ROLE_LABELS,
    effective_permissions,
    list_role_permission_map,
)
from repody.runtime.contracts.result import AppError, ErrorCode
from repody.schemas.iam import (
    CreateIamUserRequest,
    IamCatalogResponse,
    IamMeResponse,
    IamUser,
    IamUsersResponse,
    PermissionGrant,
    RoleDefinition,
    UpdateIamUserRequest,
)
from repody.settings import get_settings

router = APIRouter(prefix="/iam", tags=["iam"])


def _permission_grants(pairs: list[tuple[str, str]]) -> list[PermissionGrant]:
    return [PermissionGrant(resource=resource, action=action) for resource, action in pairs]


def _map_keycloak_user(raw: dict, roles: list[str]) -> IamUser:
    return IamUser(
        id=str(raw.get("id") or ""),
        username=str(raw.get("username") or ""),
        email=raw.get("email"),
        first_name=raw.get("firstName"),
        last_name=raw.get("lastName"),
        enabled=bool(raw.get("enabled", True)),
        roles=sorted(role for role in roles if role in APP_REALM_ROLES),
    )


def _role_names(roles: list[dict]) -> list[str]:
    return [str(role["name"]) for role in roles if role.get("name")]


@router.get("/me", response_model=IamMeResponse)
async def iam_me(principal: Principal = Depends(get_current_principal)) -> IamMeResponse:
    settings = get_settings()
    return IamMeResponse(
        subject=principal.subject,
        email=principal.email,
        roles=list(principal.roles),
        permissions=_permission_grants(effective_permissions(principal.roles)),
        can_manage_users=authorize(principal, "users", "write"),
        oidc_enabled=settings.oidc_enabled,
        keycloak_admin_url=keycloak.keycloak_console_url(settings),
    )


@router.get("/catalog", response_model=IamCatalogResponse)
async def iam_catalog(
    _principal: Principal = Depends(get_current_principal),
) -> IamCatalogResponse:
    role_map = list_role_permission_map()
    roles = [
        RoleDefinition(
            id=role_id,
            label=ROLE_LABELS.get(role_id, role_id),
            description=ROLE_DESCRIPTIONS.get(role_id, ""),
            permissions=_permission_grants(grants),
        )
        for role_id, grants in role_map.items()
    ]
    return IamCatalogResponse(roles=roles, app_roles=sorted(APP_REALM_ROLES))


@router.get(
    "/users",
    response_model=IamUsersResponse,
    dependencies=[Depends(require_permission("users", "read"))],
)
async def list_users(
    search: str | None = Query(default=None, max_length=120),
) -> IamUsersResponse:
    settings = get_settings()
    if not settings.oidc_enabled:
        return IamUsersResponse(
            users=[
                IamUser(
                    id="dev-local",
                    username="dev@local",
                    email="dev@local",
                    first_name="Dev",
                    last_name="Admin",
                    enabled=True,
                    roles=["platform_admin"],
                )
            ],
            management_available=False,
            management_error="OIDC is disabled â€” dev mode uses a synthetic platform_admin principal.",
        )

    if not keycloak.keycloak_admin_configured(settings):
        return IamUsersResponse(
            users=[],
            management_available=False,
            management_error="Keycloak admin API is not configured on the API service.",
        )

    raw_users_r = await keycloak.list_users(search=search, settings=settings)
    if not raw_users_r.is_ok:
        err = raw_users_r.error
        return IamUsersResponse(
            users=[],
            management_available=False,
            management_error=err.message if err else "Keycloak list_users failed",
        )

    users: list[IamUser] = []
    for raw in raw_users_r.unwrap():
        user_id = str(raw.get("id") or "")
        if not user_id:
            continue
        roles_r = await keycloak.user_realm_roles(user_id, settings=settings)
        if not roles_r.is_ok:
            err = roles_r.error
            return IamUsersResponse(
                users=[],
                management_available=False,
                management_error=err.message if err else "Keycloak user_realm_roles failed",
            )
        users.append(_map_keycloak_user(raw, _role_names(roles_r.unwrap())))
    users.sort(key=lambda user: (user.email or user.username).lower())
    return IamUsersResponse(users=users, management_available=True)


@router.post(
    "/users",
    response_model=IamUser,
    dependencies=[Depends(require_permission("users", "write"))],
)
async def create_user(
    body: CreateIamUserRequest,
    principal: Principal = Depends(get_current_principal),
) -> IamUser:
    settings = get_settings()
    if not settings.oidc_enabled:
        raise HTTPException(503, "User management requires OIDC/Keycloak.")

    invalid_roles = [role for role in body.roles if role not in APP_REALM_ROLES]
    if invalid_roles:
        raise HTTPException(400, f"Invalid roles: {', '.join(invalid_roles)}")
    if not body.roles:
        raise HTTPException(400, "At least one application role is required.")

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
    if not user_id_r.is_ok:
        raise_app_error(user_id_r.error or AppError(code=ErrorCode.INFRA, message="create failed"))

    user_id = user_id_r.unwrap()
    password_r = await keycloak.reset_password(
        user_id, body.password, temporary=False, settings=settings
    )
    if not password_r.is_ok:
        raise_app_error(
            password_r.error or AppError(code=ErrorCode.INFRA, message="password failed")
        )

    roles_set_r = await keycloak.set_user_app_roles(user_id, body.roles, settings=settings)
    if not roles_set_r.is_ok:
        raise_app_error(roles_set_r.error or AppError(code=ErrorCode.INFRA, message="roles failed"))

    raw_users_r = await keycloak.list_users(search=username, settings=settings)
    if not raw_users_r.is_ok:
        raise_app_error(raw_users_r.error or AppError(code=ErrorCode.INFRA, message="list failed"))
    raw = next((item for item in raw_users_r.unwrap() if str(item.get("id")) == user_id), None)
    if not raw:
        raw = {"id": user_id, "username": username, "email": username, **payload}

    roles_r = await keycloak.user_realm_roles(user_id, settings=settings)
    if not roles_r.is_ok:
        raise_app_error(
            roles_r.error or AppError(code=ErrorCode.INFRA, message="roles read failed")
        )
    return _map_keycloak_user(raw, _role_names(roles_r.unwrap()))


@router.patch(
    "/users/{user_id}",
    response_model=IamUser,
    dependencies=[Depends(require_permission("users", "write"))],
)
async def update_user(
    user_id: str,
    body: UpdateIamUserRequest,
    principal: Principal = Depends(get_current_principal),
) -> IamUser:
    settings = get_settings()
    if not settings.oidc_enabled:
        raise HTTPException(503, "User management requires OIDC/Keycloak.")
    if user_id == principal.subject and body.enabled is False:
        raise HTTPException(400, "You cannot disable your own account.")
    if user_id == principal.subject and body.roles is not None:
        if "platform_admin" not in body.roles and "platform_admin" in principal.roles:
            raise HTTPException(400, "You cannot remove your own platform_admin role.")

    raw_users_r = await keycloak.list_users(settings=settings)
    if not raw_users_r.is_ok:
        raise_app_error(raw_users_r.error or AppError(code=ErrorCode.INFRA, message="list failed"))
    raw = next((item for item in raw_users_r.unwrap() if str(item.get("id")) == user_id), None)
    if not raw:
        raise HTTPException(404, "User not found.")

    update_payload = {
        "username": raw.get("username"),
        "email": raw.get("email"),
        "emailVerified": raw.get("emailVerified", True),
        "enabled": body.enabled if body.enabled is not None else raw.get("enabled", True),
        "firstName": body.first_name if body.first_name is not None else raw.get("firstName"),
        "lastName": body.last_name if body.last_name is not None else raw.get("lastName"),
    }
    updated = await keycloak.update_user(user_id, update_payload, settings=settings)
    if not updated.is_ok:
        raise_app_error(updated.error or AppError(code=ErrorCode.INFRA, message="update failed"))

    if body.password:
        password_r = await keycloak.reset_password(
            user_id, body.password, temporary=False, settings=settings
        )
        if not password_r.is_ok:
            raise_app_error(
                password_r.error or AppError(code=ErrorCode.INFRA, message="password failed")
            )

    if body.roles is not None:
        if not body.roles:
            raise HTTPException(400, "At least one application role is required.")
        roles_set_r = await keycloak.set_user_app_roles(user_id, body.roles, settings=settings)
        if not roles_set_r.is_ok:
            raise_app_error(
                roles_set_r.error or AppError(code=ErrorCode.INFRA, message="roles failed")
            )

    refreshed_r = await keycloak.list_users(
        search=str(raw.get("username") or ""), settings=settings
    )
    if not refreshed_r.is_ok:
        raise_app_error(refreshed_r.error or AppError(code=ErrorCode.INFRA, message="list failed"))
    latest = next((item for item in refreshed_r.unwrap() if str(item.get("id")) == user_id), raw)
    roles_r = await keycloak.user_realm_roles(user_id, settings=settings)
    if not roles_r.is_ok:
        raise_app_error(
            roles_r.error or AppError(code=ErrorCode.INFRA, message="roles read failed")
        )
    return _map_keycloak_user(latest, _role_names(roles_r.unwrap()))
