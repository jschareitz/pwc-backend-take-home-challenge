from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import JSON, Column, Field, SQLModel

from app.schemas.jobs import JobType, Status


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: Optional[UUID] = Field(
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4),
        default_factory=uuid4,
    )
    job_type: JobType = Field()
    payload: Dict[str, Any] = Field(sa_column=Column(JSON))
    result: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    error_message: Optional[str] = None
    retry_count: int = Field(default=0, ge=0)
    max_retries: int = Field(default=3, ge=0)
    processing_duration_seconds: float = Field(default=0.0, ge=0.0)

    status: Status = Field(default=Status.PENDING)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
