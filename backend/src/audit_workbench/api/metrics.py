from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.api.deps import get_session
from audit_workbench.schemas.metrics import MetricsResponse
from audit_workbench.services import metrics_service

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("", response_model=MetricsResponse)
async def get_metrics(session: AsyncSession = Depends(get_session)):
    return await metrics_service.get_metrics(session)
