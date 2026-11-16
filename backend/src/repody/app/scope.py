"""Accounts: who sees and changes what.

An account is a client company (its Keycloak group, ``client-<name>``). A caller with an account
sees its workflows, the shared ones (no account: the examples, read-only) and only its own runs. A caller without one (a platform admin, or any user of a
single-client installation) sees everything. ``account`` below is the caller's (None: all).
"""

from sqlalchemy import ColumnElement, or_, true

from repody.app.errors import AppError
from repody.infra.models import Run, Workflow


def visible_workflows(account: str | None) -> ColumnElement[bool]:
    """The workflows a caller sees: not archived, and theirs or shared."""
    alive = Workflow.status != "archived"
    if account is None:
        return alive
    return alive & or_(Workflow.account_id == account, Workflow.account_id.is_(None))


def sees_workflow(wf: Workflow, account: str | None) -> bool:
    return account is None or wf.account_id in (None, account)


def own_workflow(wf: Workflow, account: str | None) -> None:
    """Changing or running a workflow: shared ones are read-only for accounts."""
    if account is not None and wf.account_id != account:
        raise AppError(403, "Examples are shared: duplicate this workflow to edit or run it.")


def visible_runs(account: str | None) -> ColumnElement[bool]:
    """The runs a caller sees: their account's (all of them without an account)."""
    return true() if account is None else Run.account_id == account
