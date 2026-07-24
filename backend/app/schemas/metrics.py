from pydantic import BaseModel


class MetricsRead(BaseModel):
    total_jobs: int
    pending_jobs: int
    processing_jobs: int
    completed_jobs: int
    failed_jobs: int
    average_processing_duration_seconds: float