from fastapi import APIRouter, Depends

from repody.api.auth import require_permission
from repody.api.deps import SessionDep
from repody.app.dashboard import get_dashboard
from repody.schemas.dashboard import DashboardResponse

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(require_permission("metrics", "read"))],
)


@router.get("", response_model=DashboardResponse)
async def dashboard_bundle(session: SessionDep):
    return await get_dashboard(session)
