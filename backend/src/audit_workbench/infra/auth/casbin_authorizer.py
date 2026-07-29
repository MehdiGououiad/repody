"""Casbin RBAC — module functions over a cached enforcer (no authorizer class)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import casbin
from casbin import Enforcer

from audit_workbench.infra.auth.principal import APP_REALM_ROLES, Principal

_AUTH_DIR = Path(__file__).resolve().parent


@lru_cache
def get_enforcer() -> Enforcer:
    return casbin.Enforcer(
        str(_AUTH_DIR / "rbac_model.conf"),
        str(_AUTH_DIR / "rbac_policy.csv"),
    )


def clear_authorizer_cache() -> None:
    get_enforcer.cache_clear()


def _sync_roles(enforcer: Enforcer, principal: Principal) -> None:
    subject = principal.subject
    enforcer.delete_roles_for_user(subject)
    for role in principal.roles:
        if role in APP_REALM_ROLES:
            enforcer.add_role_for_user(subject, role)


def authorize(principal: Principal, resource: str, action: str) -> bool:
    enforcer = get_enforcer()
    _sync_roles(enforcer, principal)
    return bool(enforcer.enforce(principal.subject, resource, action))
