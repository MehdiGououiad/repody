from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.api.deps import get_session
from audit_workbench.auth.dependencies import require_permission
from audit_workbench.schemas.dashboard import DashboardResponse
from audit_workbench.services.dashboard_service import get_dashboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "",
    response_model=DashboardResponse,
    dependencies=[Depends(require_permission("metrics", "read"))],
)
async def dashboard_bundle(session: AsyncSession = Depends(get_session)):
    return await get_dashboard(session)
