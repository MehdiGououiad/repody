"""Domain-agnostic cases API routes."""

from typing import Annotated

from fastapi import APIRouter

from repody_core.api.deps import StoreDep, require
from repody_core.app import cases as app_cases
from repody_core.infra.auth import CoreUser
from repody_core.schemas.cases import CaseResponse, CreateCaseRequest

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", status_code=201)
async def create_case(
    body: CreateCaseRequest,
    store: StoreDep,
    user: Annotated[CoreUser, require("case:write")],
) -> CaseResponse:
    """Create a domain-agnostic case (supports zero-document payloads)."""
    return await app_cases.create_case(
        store,
        actor_sub=user.subject,
        account_id=user.account,
        request=body,
    )


@router.get("/{case_id}")
async def get_case(
    case_id: str,
    store: StoreDep,
    user: Annotated[CoreUser, require("case:read")],
) -> CaseResponse:
    """Retrieve a case scoped to the caller's account."""
    return await app_cases.get_case(store, case_id=case_id, account_id=user.account)
