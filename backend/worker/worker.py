import logging
import os
import random
import time
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.db.models import Job
from app.db.session import engine
from app.schemas.jobs import Status
from app.core.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def _get_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("Invalid %s=%r, falling back to %s", name, raw, default)
        return default


FAILURE_RATE = max(0.0, min(1.0, _get_float_env("WORKER_FAILURE_RATE", 0.2)))
MIN_WORK_SECONDS = max(0.0, _get_float_env("WORKER_MIN_WORK_SECONDS", 2.0))
MAX_WORK_SECONDS = max(MIN_WORK_SECONDS, _get_float_env("WORKER_MAX_WORK_SECONDS", 5.0))
POLL_INTERVAL_SECONDS = max(0.1, _get_float_env("WORKER_POLL_INTERVAL_SECONDS", 1.0))


def claim_job(session: Session) -> Job | None:
    statement = (
        select(Job)
        .where(Job.status == Status.PENDING)
        .order_by(Job.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    result = session.exec(statement)
    return result.one_or_none()


def process_job(job: Job, session: Session) -> None:
    job.status = Status.PROCESSING
    job.started_at = datetime.now(timezone.utc)
    session.add(job)
    session.commit()

    attempt_duration = random.uniform(MIN_WORK_SECONDS, MAX_WORK_SECONDS)
    logger.info("Processing job %s for %.2fs", job.id, attempt_duration)
    time.sleep(attempt_duration)

    job.processing_duration_seconds += attempt_duration
    if random.random() < FAILURE_RATE:
        job.retry_count += 1
        job.error_message = "Simulated worker failure"
        if job.retry_count < job.max_retries:
            job.status = Status.PENDING
            job.finished_at = None
            logger.info(
                "Job %s failed, retry %s/%s",
                job.id,
                job.retry_count,
                job.max_retries,
            )
        else:
            job.status = Status.FAILED
            job.finished_at = datetime.now(timezone.utc)
            logger.info(
                "Job %s permanently failed after %s attempts",
                job.id,
                job.retry_count,
            )
    else:
        job.status = Status.COMPLETED
        job.error_message = None
        job.result = {"message": "processed", "result_path": f"results/{job.id}/"}
        job.finished_at = datetime.now(timezone.utc)
        logger.info("Job %s completed", job.id)

    session.add(job)
    session.commit()


def run_worker() -> None:
    logger.info("Starting worker against database")
    with Session(engine) as session:
        while True:
            try:
                job = claim_job(session)
                if job is None:
                    session.rollback()
                    logger.debug("No pending jobs, sleeping %ss", POLL_INTERVAL_SECONDS)
                    time.sleep(POLL_INTERVAL_SECONDS)
                    continue

                process_job(job, session)
            except SQLAlchemyError as error:
                logger.exception("Database error while processing jobs: %s", error)
                session.rollback()
                time.sleep(POLL_INTERVAL_SECONDS)
            except Exception as error:
                logger.exception("Unexpected error in worker: %s", error)
                session.rollback()
                time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_worker()
