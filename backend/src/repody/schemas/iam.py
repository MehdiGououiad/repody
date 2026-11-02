from __future__ import annotations

from pydantic import Field

from repody.schemas.common import CamelModel


class PermissionGrant(CamelModel):
    resource: str
    action: str


class RoleDefinition(CamelModel):
    id: str
    label: str
    description: str
    permissions: list[PermissionGrant]


class IamUser(CamelModel):
    id: str
    username: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    enabled: bool = True
    roles: list[str] = Field(default_factory=list)


class IamMeResponse(CamelModel):
    subject: str
    email: str | None = None
    roles: list[str]
    permissions: list[PermissionGrant]
    can_manage_users: bool
    oidc_enabled: bool
    keycloak_admin_url: str | None = None


class IamCatalogResponse(CamelModel):
    roles: list[RoleDefinition]
    app_roles: list[str]


class IamUsersResponse(CamelModel):
    users: list[IamUser]
    management_available: bool
    management_error: str | None = None


class CreateIamUserRequest(CamelModel):
    email: str
    first_name: str = ""
    last_name: str = ""
    password: str = Field(min_length=8)
    roles: list[str] = Field(default_factory=lambda: ["viewer"])
    enabled: bool = True


class UpdateIamUserRequest(CamelModel):
    first_name: str | None = None
    last_name: str | None = None
    enabled: bool | None = None
    roles: list[str] | None = None
    password: str | None = Field(default=None, min_length=8)
