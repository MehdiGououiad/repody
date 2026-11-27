"""Use cases for domain-agnostic cases."""

from repody_common.ids import new_id
from repody_core.app.ports import CoreStore
from repody_core.schemas.cases import CaseResponse, CreateCaseRequest
from repody_core.schemas.errors import NotFoundError


async def create_case(
    store: CoreStore,
    *,
    actor_sub: str,
    account_id: str | None,
    request: CreateCaseRequest,
) -> CaseResponse:
    """Create a case with optional artifacts, JSON payload, or both."""
    scoped_request = request.model_copy(
        update={"account_id": account_id if account_id is not None else request.account_id}
    )
    return await store.create_case(
        case_id=new_id("case"),
        actor_sub=actor_sub,
        request=scoped_request,
    )


async def get_case(store: CoreStore, *, case_id: str, account_id: str | None) -> CaseResponse:
    """Fetch a case scoped to ``account_id`` (or raise 404)."""
    case = await store.get_case(case_id, account=account_id)
    if case is None:
        raise NotFoundError(f"Case {case_id} was not found.")
    return case
