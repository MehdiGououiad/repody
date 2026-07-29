from repody.infra.auth.casbin_authorizer import authorize
from repody.infra.auth.principal import Principal


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
