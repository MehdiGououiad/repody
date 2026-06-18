"""Read Casbin policy matrix for IAM UI."""

from __future__ import annotations

from audit_workbench.auth.casbin_authorizer import get_authorizer
from audit_workbench.auth.principal import APP_REALM_ROLES

ROLE_LABELS: dict[str, str] = {
    "platform_admin": "Platform admin",
    "admin": "Admin",
    "operator": "Operator",
    "viewer": "Viewer",
}

ROLE_DESCRIPTIONS: dict[str, str] = {
    "platform_admin": "Full access to every resource, including user management.",
    "admin": "Manage workflows, runs, settings, operator actions, and users.",
    "operator": "Build workflows, execute runs, and use diagnostics — no admin settings.",
    "viewer": "Read-only access to workflows, runs, audits, and models.",
}


def _permissions_for_role(role: str) -> list[tuple[str, str]]:
    enforcer = get_authorizer()._enforcer
    rows = enforcer.get_filtered_policy(0, role)
    return [(row[1], row[2]) for row in rows if len(row) >= 3]


def list_role_permission_map() -> dict[str, list[tuple[str, str]]]:
    return {role: _permissions_for_role(role) for role in sorted(APP_REALM_ROLES)}


def effective_permissions(roles: tuple[str, ...] | list[str]) -> list[tuple[str, str]]:
    if "platform_admin" in roles:
        return [("*", "*")]
    seen: set[tuple[str, str]] = set()
    ordered: list[tuple[str, str]] = []
    for role in roles:
        for grant in _permissions_for_role(role):
            if grant not in seen:
                seen.add(grant)
                ordered.append(grant)
    return sorted(ordered, key=lambda item: (item[0], item[1]))
