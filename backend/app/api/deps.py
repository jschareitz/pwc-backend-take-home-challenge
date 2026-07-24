from fastapi import Depends
from sqlmodel import Session

from app.db.session import get_session
from app.services.jobs import JobService
from app.services.metrics import MetricsService


def get_job_service(session: Session = Depends(get_session)) -> JobService:
    return JobService(session)


def get_metrics_service(session: Session = Depends(get_session)) -> MetricsService:
    return MetricsService(session)
