from fastapi import APIRouter, Depends

from repody.api.deps import SessionDep
from repody.app.dashboard import get_dashboard
from repody.infra.auth.dependencies import require_permission
from repody.schemas.dashboard import DashboardResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "",
    response_model=DashboardResponse,
    dependencies=[Depends(require_permission("metrics", "read"))],
)
async def dashboard_bundle(session: SessionDep):
    return await get_dashboard(session)
