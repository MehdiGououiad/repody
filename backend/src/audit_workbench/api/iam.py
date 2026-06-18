"""Identity and access management — Casbin matrix + Keycloak user admin."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from audit_workbench.auth.casbin_authorizer import get_authorizer
from audit_workbench.auth.dependencies import get_current_principal, require_permission
from audit_workbench.auth.keycloak_admin import (
    KeycloakAdminClient,
    KeycloakAdminError,
    keycloak_console_url,
)
from audit_workbench.auth.principal import APP_REALM_ROLES, Principal
from audit_workbench.auth.rbac_catalog import (
    ROLE_DESCRIPTIONS,
    ROLE_LABELS,
    effective_permissions,
    list_role_permission_map,
)
from audit_workbench.schemas.iam import (
    CreateIamUserRequest,
    IamCatalogResponse,
    IamMeResponse,
    IamUser,
    IamUsersResponse,
    PermissionGrant,
    RoleDefinition,
    UpdateIamUserRequest,
)
from audit_workbench.settings import get_settings

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


@router.get("/me", response_model=IamMeResponse)
async def iam_me(principal: Principal = Depends(get_current_principal)) -> IamMeResponse:
    settings = get_settings()
    authorizer = get_authorizer()
    can_manage = authorizer.authorize(principal, "users", "write")
    return IamMeResponse(
        subject=principal.subject,
        email=principal.email,
        roles=list(principal.roles),
        permissions=_permission_grants(effective_permissions(principal.roles)),
        can_manage_users=can_manage,
        oidc_enabled=settings.oidc_enabled,
        keycloak_admin_url=keycloak_console_url(settings),
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
            management_error="OIDC is disabled — dev mode uses a synthetic platform_admin principal.",
        )

    client = KeycloakAdminClient(settings)
    if not client.configured:
        return IamUsersResponse(
            users=[],
            management_available=False,
            management_error="Keycloak admin API is not configured on the API service.",
        )

    try:
        raw_users = await client.list_users(search=search)
        users: list[IamUser] = []
        for raw in raw_users:
            user_id = str(raw.get("id") or "")
            if not user_id:
                continue
            roles = [role["name"] for role in await client.user_realm_roles(user_id)]
            users.append(_map_keycloak_user(raw, roles))
        users.sort(key=lambda user: (user.email or user.username).lower())
        return IamUsersResponse(users=users, management_available=True)
    except KeycloakAdminError as exc:
        return IamUsersResponse(
            users=[],
            management_available=False,
            management_error=str(exc),
        )


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

    client = KeycloakAdminClient(settings)
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
    try:
        user_id = await client.create_user(payload)
        await client.reset_password(user_id, body.password, temporary=False)
        await client.set_user_app_roles(user_id, body.roles)
        raw_users = await client.list_users(search=username)
        raw = next((item for item in raw_users if str(item.get("id")) == user_id), None)
        if not raw:
            raw = {"id": user_id, "username": username, "email": username, **payload}
        roles = await client.user_realm_roles(user_id)
        return _map_keycloak_user(raw, [role["name"] for role in roles])
    except KeycloakAdminError as exc:
        raise HTTPException(exc.status_code or 502, str(exc)) from exc


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

    client = KeycloakAdminClient(settings)
    try:
        raw_users = await client.list_users()
        raw = next((item for item in raw_users if str(item.get("id")) == user_id), None)
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
        await client.update_user(user_id, update_payload)
        if body.password:
            await client.reset_password(user_id, body.password, temporary=False)
        if body.roles is not None:
            if not body.roles:
                raise HTTPException(400, "At least one application role is required.")
            await client.set_user_app_roles(user_id, body.roles)

        refreshed = await client.list_users(search=str(raw.get("username") or ""))
        latest = next((item for item in refreshed if str(item.get("id")) == user_id), raw)
        roles = [role["name"] for role in await client.user_realm_roles(user_id)]
        return _map_keycloak_user(latest, roles)
    except KeycloakAdminError as exc:
        raise HTTPException(exc.status_code or 502, str(exc)) from exc
