"""Casbin RBAC — immutable shared enforcer; JWT roles checked as policy subjects."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import casbin
from casbin import Enforcer

from repody.infra.auth.principal import APP_REALM_ROLES, Principal

_AUTH_DIR = Path(__file__).resolve().parent


@lru_cache
def get_enforcer() -> Enforcer:
    """Load policy once. Never mutate grouping or policy at request time."""
    return casbin.Enforcer(
        str(_AUTH_DIR / "rbac_model.conf"),
        str(_AUTH_DIR / "rbac_policy.csv"),
    )


def clear_authorizer_cache() -> None:
    get_enforcer.cache_clear()


def authorize(principal: Principal, resource: str, action: str) -> bool:
    """Allow if any JWT app role is granted the (resource, action) in policy.csv.

    Policy subjects are role names (admin, operator, …). We enforce with the role
    as ``sub`` so the shared enforcer stays read-only under concurrency.
    """
    enforcer = get_enforcer()
    for role in principal.roles:
        if role in APP_REALM_ROLES and enforcer.enforce(role, resource, action):
            return True
    return False
