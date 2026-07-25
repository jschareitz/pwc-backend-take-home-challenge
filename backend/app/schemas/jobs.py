from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Status(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(str, Enum):
    IMAGE_RESIZE = "image_resize"
    REPORT_GENERATION = "report_generation"
    DATA_IMPORT = "data_import"


class JobCreate(BaseModel):
    job_type: JobType
    payload: dict[str, Any]
    max_retries: int = Field(default=3, ge=0, le=10)

    @field_validator("payload")
    @classmethod
    def payload_must_not_be_empty(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value:
            raise ValueError("payload must not be empty")
        return value


class JobRead(BaseModel):
    id: UUID
    job_type: JobType
    payload: dict[str, Any]
    status: Status = Status.PENDING
    result: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    retry_count: int = 0
    max_retries: int = 3
    processing_duration_seconds: float = 0.0

    model_config = ConfigDict(from_attributes=True)
