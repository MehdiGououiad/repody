from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from repody.api.deps import get_session
from repody.schemas.metrics import MetricsResponse
from repody.app import metrics as metrics_app

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("", response_model=MetricsResponse)
async def get_metrics(session: AsyncSession = Depends(get_session)):
    return await metrics_app.get_metrics(session)
