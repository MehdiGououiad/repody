"""Unit tests for Casbin RBAC (read-only shared enforcer)."""

from __future__ import annotations

from repody.infra.auth.casbin_authorizer import authorize, clear_authorizer_cache
from repody.infra.auth.principal import Principal


def setup_function() -> None:
    clear_authorizer_cache()


def test_platform_admin_has_full_access() -> None:
    principal = Principal(subject="u1", roles=("platform_admin",))
    assert authorize(principal, "workflow", "delete")
    assert authorize(principal, "operator", "execute")


def test_viewer_cannot_write_workflows() -> None:
    principal = Principal(subject="u2", roles=("viewer",))
    assert authorize(principal, "workflow", "read")
    assert not authorize(principal, "workflow", "write")


def test_operator_can_execute_runs() -> None:
    principal = Principal(subject="u3", roles=("operator",))
    assert authorize(principal, "run", "execute")
    assert authorize(principal, "operator", "execute")
    assert not authorize(principal, "settings", "write")


def test_unknown_role_is_denied() -> None:
    principal = Principal(subject="u4", roles=("not-a-role",))
    assert not authorize(principal, "workflow", "read")


def test_empty_roles_denied() -> None:
    principal = Principal(subject="u5", roles=())
    assert not authorize(principal, "run", "execute")


def test_any_matching_role_allows() -> None:
    principal = Principal(subject="u6", roles=("viewer", "operator"))
    assert authorize(principal, "run", "execute")
    assert authorize(principal, "workflow", "read")
