from fastapi import APIRouter

from repody.api.deps import SessionDep
from repody.app.dashboard import get_dashboard
from repody.schemas.dashboard import DashboardResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def dashboard_bundle(session: SessionDep):
    return await get_dashboard(session)
