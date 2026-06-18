from __future__ import annotations

from pydantic import Field

from audit_workbench.schemas.common import CamelModel


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
    first_name: str | None = Field(default=None, serialization_alias="firstName")
    last_name: str | None = Field(default=None, serialization_alias="lastName")
    enabled: bool = True
    roles: list[str] = Field(default_factory=list)


class IamMeResponse(CamelModel):
    subject: str
    email: str | None = None
    roles: list[str]
    permissions: list[PermissionGrant]
    can_manage_users: bool = Field(serialization_alias="canManageUsers")
    oidc_enabled: bool = Field(serialization_alias="oidcEnabled")
    keycloak_admin_url: str | None = Field(default=None, serialization_alias="keycloakAdminUrl")


class IamCatalogResponse(CamelModel):
    roles: list[RoleDefinition]
    app_roles: list[str] = Field(serialization_alias="appRoles")


class IamUsersResponse(CamelModel):
    users: list[IamUser]
    management_available: bool = Field(serialization_alias="managementAvailable")
    management_error: str | None = Field(default=None, serialization_alias="managementError")


class CreateIamUserRequest(CamelModel):
    email: str
    first_name: str = Field(default="", serialization_alias="firstName")
    last_name: str = Field(default="", serialization_alias="lastName")
    password: str = Field(min_length=8)
    roles: list[str] = Field(default_factory=lambda: ["viewer"])
    enabled: bool = True


class UpdateIamUserRequest(CamelModel):
    first_name: str | None = Field(default=None, serialization_alias="firstName")
    last_name: str | None = Field(default=None, serialization_alias="lastName")
    enabled: bool | None = None
    roles: list[str] | None = None
    password: str | None = Field(default=None, min_length=8)
