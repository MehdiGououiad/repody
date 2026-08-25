from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from repody.api.deps import get_session
from repody.app.dashboard import get_dashboard
from repody.infra.auth.dependencies import require_permission
from repody.schemas.dashboard import DashboardResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "",
    response_model=DashboardResponse,
    dependencies=[Depends(require_permission("metrics", "read"))],
)
async def dashboard_bundle(session: AsyncSession = Depends(get_session)):
    return await get_dashboard(session)
