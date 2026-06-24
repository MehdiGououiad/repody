from audit_workbench.auth.casbin_authorizer import CasbinAuthorizer
from audit_workbench.auth.principal import Principal


def test_platform_admin_has_full_access() -> None:
    authorizer = CasbinAuthorizer()
    principal = Principal(subject="u1", roles=("platform_admin",))
    assert authorizer.authorize(principal, "workflow", "delete")
    assert authorizer.authorize(principal, "operator", "execute")


def test_viewer_cannot_write_workflows() -> None:
    authorizer = CasbinAuthorizer()
    principal = Principal(subject="u2", roles=("viewer",))
    assert authorizer.authorize(principal, "workflow", "read")
    assert not authorizer.authorize(principal, "workflow", "write")


def test_operator_can_execute_runs() -> None:
    authorizer = CasbinAuthorizer()
    principal = Principal(subject="u3", roles=("operator",))
    assert authorizer.authorize(principal, "run", "execute")
    assert authorizer.authorize(principal, "operator", "execute")
    assert not authorizer.authorize(principal, "settings", "write")
