from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi import status as http_status

from app.api.deps import get_job_service
from app.schemas.jobs import Status, JobCreate, JobRead
from app.services.jobs import JobService

router = APIRouter(prefix="/jobs")


@router.get(
    "",
    response_model=List[JobRead],
    status_code=http_status.HTTP_200_OK,
)
def get_jobs(
    status: Status | None = Query(default=None, alias="status", description="Filter jobs by status"),
    limit: int = Query(default=100, ge=1, le=500, description="Number of jobs to retrieve"),
    job_service: JobService = Depends(get_job_service),
):
    return job_service.get_jobs(status=status, limit=limit)


@router.get(
    "/{id}",
    response_model=JobRead,
    status_code=http_status.HTTP_200_OK,
)
def get_job(id: UUID, job_service: JobService = Depends(get_job_service)):
    return job_service.get_job(id)


@router.post(
    "",
    response_model=JobRead,
    status_code=http_status.HTTP_201_CREATED,
)
def create_job(data: JobCreate, job_service: JobService = Depends(get_job_service)):
    return job_service.create_job(data)


# Bonusaufgabe
@router.delete("/{id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_job(id: UUID, job_service: JobService = Depends(get_job_service)):
    return job_service.delete_job(id)
    
