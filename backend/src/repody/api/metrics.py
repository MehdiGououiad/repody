from fastapi import APIRouter, Depends

from repody.api.auth import require_permission
from repody.api.deps import SessionDep
from repody.app import metrics as metrics_app
from repody.schemas.metrics import MetricsResponse

router = APIRouter(
    prefix="/metrics",
    tags=["metrics"],
    dependencies=[Depends(require_permission("metrics", "read"))],
)


@router.get("", response_model=MetricsResponse)
async def get_metrics(session: SessionDep):
    return await metrics_app.get_metrics(session)
