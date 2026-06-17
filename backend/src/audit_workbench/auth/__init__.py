"""OIDC authentication (Keycloak) and Casbin authorization."""

from audit_workbench.auth.dependencies import (
    get_current_principal,
    require_admin,
    require_admin_or_workflow_run,
    require_management_access,
    require_permission,
    require_run_create_access,
)
from audit_workbench.auth.principal import APP_REALM_ROLES, Principal

__all__ = [
    "APP_REALM_ROLES",
    "Principal",
    "get_current_principal",
    "require_admin",
    "require_admin_or_workflow_run",
    "require_management_access",
    "require_permission",
    "require_run_create_access",
]
