import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.core.exceptions import JobAlreadyStartedException, JobNotFoundException
from app.db.models import Job
from app.schemas.jobs import JobCreate, Status

logger = logging.getLogger(__name__)


class JobService:
    def __init__(self, session: Session):
        self.session = session

    def get_job(self, job_id: UUID) -> Job:
        statement = select(Job).where(Job.id == job_id)
        job = self.session.exec(statement).one_or_none()
        if job is None:
            logger.warning(f"Job not found: {job_id}")
            raise JobNotFoundException(job_id)
        logger.debug(f"Retrieved job: {job_id} (status={job.status})")
        return job

    def get_jobs(self, status: Optional[Status] = None, limit: int = 100) -> List[Job]:
        statement = select(Job)
        if status is not None:
            statement = statement.where(Job.status == status)
        statement = statement.limit(limit).order_by(Job.created_at.desc())
        jobs = self.session.exec(statement).all()
        logger.info(f"Retrieved {len(jobs)} jobs (status={status}, limit={limit})")
        return jobs

    def create_job(self, job_create: JobCreate) -> Job:
        job = Job(
            job_type=job_create.job_type,
            payload=job_create.payload,
            max_retries=job_create.max_retries,
        )
        try:
            self.session.add(job)
            self.session.commit()
            self.session.refresh(job)
            logger.info(f"Created job: {job.id} (type={job.job_type})")
            return job
        except SQLAlchemyError:
            self.session.rollback()
            logger.error(f"Failed to create job (type={job_create.job_type})")
            raise

    def delete_job(self, job_id: UUID) -> None:
        try:
            job = self.get_job(job_id)
            if job.status != Status.PENDING:
                logger.warning(f"Cannot delete job {job_id}: status is {job.status} (must be PENDING)")
                raise JobAlreadyStartedException(job_id)
            self.session.delete(job)
            self.session.commit()
            logger.info(f"Deleted job: {job_id}")
        except SQLAlchemyError:
            self.session.rollback()
            logger.error(f"Failed to delete job: {job_id}")
            raise
