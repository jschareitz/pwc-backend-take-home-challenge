import os
from uuid import uuid4

import pytest
from sqlmodel import Session, create_engine, select

from app.db.models import Job
from app.schemas.jobs import JobType, Status

pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module")
def e2e_engine():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip(
            "DATABASE_URL not set. Run this test via docker-compose.e2e test service."
        )
    return create_engine(database_url, pool_pre_ping=True)


def test_row_level_lock_skip_locked_allows_only_one_claimer(e2e_engine) -> None:
    with Session(e2e_engine) as setup_session:
        job = Job(
            job_type=JobType.IMAGE_RESIZE,
            payload={
                "source": "lock-in.png",
                "target": "lock-out.png",
                "request_id": str(uuid4()),
            },
            status=Status.COMPLETED,
            max_retries=3,
        )
        setup_session.add(job)
        setup_session.commit()
        setup_session.refresh(job)

    lock_stmt = (
        select(Job).where(Job.id == job.id).with_for_update(skip_locked=True).limit(1)
    )

    with Session(e2e_engine) as worker_a, Session(e2e_engine) as worker_b:
        claimed_by_a = worker_a.exec(lock_stmt).one_or_none()
        assert claimed_by_a is not None
        assert claimed_by_a.id == job.id

        claimed_by_b = worker_b.exec(lock_stmt).one_or_none()
        assert claimed_by_b is None

        worker_a.rollback()

        claimed_after_release = worker_b.exec(lock_stmt).one_or_none()
        assert claimed_after_release is not None
        assert claimed_after_release.id == job.id
        worker_b.rollback()
