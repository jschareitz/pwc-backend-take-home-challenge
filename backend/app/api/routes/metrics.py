from fastapi import APIRouter, Depends, status

from app.api.deps import get_metrics_service
from app.schemas.metrics import MetricsRead
from app.services.metrics import MetricsService

router = APIRouter(prefix="/metrics")


@router.get("", response_model=MetricsRead, status_code=status.HTTP_200_OK)
def get_metrics(metrics_service: MetricsService = Depends(get_metrics_service)):
    return metrics_service.get_metrics()
