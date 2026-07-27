"""IDP agent — extract + validate for a claimed Run."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from audit_workbench.agents.idp.contracts import IdpInput, IdpOutcome

if TYPE_CHECKING:
    from audit_workbench.agents.idp.run import execute_idp_run as execute_idp_run

__all__ = ["IdpInput", "IdpOutcome", "execute_idp_run"]


def __getattr__(name: str) -> Any:
    if name == "execute_idp_run":
        from audit_workbench.agents.idp.run import execute_idp_run

        return execute_idp_run
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
