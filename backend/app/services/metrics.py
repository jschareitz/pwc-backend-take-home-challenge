from sqlmodel import Session, func, select

from app.db.models import Job
from app.schemas.jobs import Status


class MetricsService:
    def __init__(self, session: Session):
        self.session = session

    def get_metrics(self) -> dict[str, int | float]:
        statement = select(
            func.count().label("total_jobs"),
            func.count().filter(Job.status == Status.PENDING).label("pending_jobs"),
            func.count()
            .filter(Job.status == Status.PROCESSING)
            .label("processing_jobs"),
            func.count().filter(Job.status == Status.COMPLETED).label("completed_jobs"),
            func.count().filter(Job.status == Status.FAILED).label("failed_jobs"),
            func.avg(Job.processing_duration_seconds)
            .filter(Job.status == Status.COMPLETED)
            .label("average_processing_duration_seconds"),
        ).select_from(Job)

        row = self.session.exec(statement).one()

        return {
            "total_jobs": int(row.total_jobs),
            "pending_jobs": int(row.pending_jobs),
            "processing_jobs": int(row.processing_jobs),
            "completed_jobs": int(row.completed_jobs),
            "failed_jobs": int(row.failed_jobs),
            "average_processing_duration_seconds": float(
                row.average_processing_duration_seconds or 0.0
            ),
        }
