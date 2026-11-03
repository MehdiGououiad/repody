"""Role → permission map for the Keycloak realm roles (replaces the Casbin policy file)."""

from __future__ import annotations

from repody.infra.auth.principal import Principal

Permission = tuple[str, str]  # (resource, action)

_READ_ONLY: frozenset[Permission] = frozenset(
    {
        ("workflow", "read"),
        ("run", "read"),
        ("audit", "read"),
        ("models", "read"),
        ("rules", "read"),
    }
)
_OPERATOR: frozenset[Permission] = _READ_ONLY | {
    ("workflow", "write"),
    ("run", "execute"),
    ("upload", "write"),
    ("metrics", "read"),
    ("settings", "read"),
}
_ADMIN: frozenset[Permission] = _OPERATOR | {
    ("workflow", "delete"),
    ("settings", "write"),
}

ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "viewer": _READ_ONLY,
    "operator": _OPERATOR,
    "admin": _ADMIN,
}
SUPERUSER_ROLE = "platform_admin"


def authorize(principal: Principal, resource: str, action: str) -> bool:
    """Allow if any of the principal's realm roles grants ``(resource, action)``."""
    if SUPERUSER_ROLE in principal.roles:
        return True
    return any(
        (resource, action) in ROLE_PERMISSIONS.get(role, frozenset()) for role in principal.roles
    )
