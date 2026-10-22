"""Identity and access management - Casbin matrix + Keycloak user admin."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from repody.api.auth import PrincipalDep, require_permission
from repody.api.errors import unwrap_or_raise
from repody.app import users
from repody.infra.auth import keycloak_admin as keycloak
from repody.infra.auth.casbin_authorizer import authorize
from repody.infra.auth.principal import APP_REALM_ROLES
from repody.infra.auth.rbac_catalog import (
    ROLE_DESCRIPTIONS,
    ROLE_LABELS,
    effective_permissions,
    list_role_permission_map,
)
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


@router.get("/me", response_model=IamMeResponse)
async def iam_me(principal: PrincipalDep) -> IamMeResponse:
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
    _principal: PrincipalDep,
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
    return await users.list_users(search)


@router.post(
    "/users",
    response_model=IamUser,
    dependencies=[Depends(require_permission("users", "write"))],
)
async def create_user(body: CreateIamUserRequest) -> IamUser:
    return unwrap_or_raise(await users.create_user(body))


@router.patch(
    "/users/{user_id}",
    response_model=IamUser,
    dependencies=[Depends(require_permission("users", "write"))],
)
async def update_user(
    user_id: str,
    body: UpdateIamUserRequest,
    principal: PrincipalDep,
) -> IamUser:
    return unwrap_or_raise(await users.update_user(user_id, body, principal))
