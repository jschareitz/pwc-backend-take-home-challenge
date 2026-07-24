from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.exceptions import JobAlreadyStartedException, JobNotFoundException
from app.schemas.jobs import Status
from app.services.jobs import JobService
from app.services.metrics import MetricsService

pytestmark = pytest.mark.unit


class _FakeJob:
    def __init__(self, status: Status):
        self.status = status


def test_metrics_service_maps_aggregate_row_to_response_dict() -> None:
    row = SimpleNamespace(
        total_jobs=6,
        pending_jobs=2,
        processing_jobs=1,
        completed_jobs=2,
        failed_jobs=1,
        average_processing_duration_seconds=3.75,
    )

    class FakeResult:
        def one(self):
            return row

    class FakeSession:
        def exec(self, _statement):
            return FakeResult()

    service = MetricsService(FakeSession())

    metrics = service.get_metrics()

    assert metrics == {
        "total_jobs": 6,
        "pending_jobs": 2,
        "processing_jobs": 1,
        "completed_jobs": 2,
        "failed_jobs": 1,
        "average_processing_duration_seconds": 3.75,
    }


def test_metrics_service_defaults_avg_to_zero_when_none() -> None:
    row = SimpleNamespace(
        total_jobs=0,
        pending_jobs=0,
        processing_jobs=0,
        completed_jobs=0,
        failed_jobs=0,
        average_processing_duration_seconds=None,
    )

    class FakeResult:
        def one(self):
            return row

    class FakeSession:
        def exec(self, _statement):
            return FakeResult()

    service = MetricsService(FakeSession())

    metrics = service.get_metrics()

    assert metrics["average_processing_duration_seconds"] == 0.0


def test_delete_job_deletes_when_pending() -> None:
    class FakeSession:
        def __init__(self):
            self.deleted = None
            self.committed = False
            self.rolled_back = False

        def delete(self, job):
            self.deleted = job

        def commit(self):
            self.committed = True

        def rollback(self):
            self.rolled_back = True

    session = FakeSession()
    service = JobService(session)
    pending_job = _FakeJob(Status.PENDING)
    service.get_job = lambda _job_id: pending_job

    service.delete_job(uuid4())

    assert session.deleted is pending_job
    assert session.committed is True
    assert session.rolled_back is False


@pytest.mark.parametrize("status", [Status.PROCESSING, Status.COMPLETED])
def test_delete_job_rejects_when_already_started_or_finished(status: Status) -> None:
    class FakeSession:
        def __init__(self):
            self.deleted = None
            self.committed = False
            self.rolled_back = False

        def delete(self, job):
            self.deleted = job

        def commit(self):
            self.committed = True

        def rollback(self):
            self.rolled_back = True

    session = FakeSession()
    service = JobService(session)
    service.get_job = lambda _job_id: _FakeJob(status)

    with pytest.raises(JobAlreadyStartedException):
        service.delete_job(uuid4())

    assert session.deleted is None
    assert session.committed is False
    assert session.rolled_back is False


def test_get_job_raises_not_found_exception() -> None:
    class FakeResult:
        def one_or_none(self):
            return None

    class FakeSession:
        def exec(self, _statement):
            return FakeResult()

    service = JobService(FakeSession())

    with pytest.raises(JobNotFoundException):
        service.get_job(uuid4())
