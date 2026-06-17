"""Casbin RBAC — static policies, Keycloak realm roles synced per request."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import casbin

from audit_workbench.auth.principal import APP_REALM_ROLES, Principal

_AUTH_DIR = Path(__file__).resolve().parent


@lru_cache
def get_authorizer() -> CasbinAuthorizer:
    return CasbinAuthorizer()


class CasbinAuthorizer:
    def __init__(self) -> None:
        self._enforcer = casbin.Enforcer(
            str(_AUTH_DIR / "rbac_model.conf"),
            str(_AUTH_DIR / "rbac_policy.csv"),
        )

    def _sync_roles(self, principal: Principal) -> None:
        subject = principal.subject
        self._enforcer.delete_roles_for_user(subject)
        for role in principal.roles:
            if role in APP_REALM_ROLES:
                self._enforcer.add_role_for_user(subject, role)

    def authorize(self, principal: Principal, resource: str, action: str) -> bool:
        self._sync_roles(principal)
        return self._enforcer.enforce(principal.subject, resource, action)

    def clear_cache(self) -> None:
        get_authorizer.cache_clear()
