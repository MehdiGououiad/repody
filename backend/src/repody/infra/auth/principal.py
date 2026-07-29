"""Authenticated caller identity."""

from __future__ import annotations

from dataclasses import dataclass

# Realm roles provisioned in Keycloak and enforced via Casbin.
APP_REALM_ROLES = frozenset({"platform_admin", "admin", "operator", "viewer"})


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    roles: tuple[str, ...]
    email: str | None = None

    def has_app_role(self) -> bool:
        return bool(set(self.roles) & APP_REALM_ROLES)
