"""Role → permission map for Keycloak realm roles."""

from __future__ import annotations

from repody.infra.auth.permissions import authorize
from repody.infra.auth.principal import Principal


def test_platform_admin_has_full_access() -> None:
    principal = Principal(subject="u1", roles=("platform_admin",))
    assert authorize(principal, "workflow", "delete")
    assert authorize(principal, "anything", "at-all")


def test_viewer_cannot_write_workflows() -> None:
    principal = Principal(subject="u2", roles=("viewer",))
    assert authorize(principal, "workflow", "read")
    assert not authorize(principal, "workflow", "write")
    assert not authorize(principal, "metrics", "read")


def test_operator_can_execute_runs() -> None:
    principal = Principal(subject="u3", roles=("operator",))
    assert authorize(principal, "run", "execute")
    assert authorize(principal, "settings", "read")
    assert not authorize(principal, "settings", "write")
    assert not authorize(principal, "workflow", "delete")


def test_admin_adds_delete_and_settings_write() -> None:
    principal = Principal(subject="u4", roles=("admin",))
    assert authorize(principal, "workflow", "delete")
    assert authorize(principal, "settings", "write")


def test_unknown_role_has_no_permissions() -> None:
    assert not authorize(Principal(subject="u5", roles=("stranger",)), "workflow", "read")
