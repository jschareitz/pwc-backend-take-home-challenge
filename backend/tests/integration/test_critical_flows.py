from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db.models import Job
from app.schemas.jobs import JobType, Status

pytestmark = pytest.mark.integration


def _create_job(client: TestClient) -> str:
    response = client.post(
        "/jobs",
        json={
            "job_type": JobType.IMAGE_RESIZE.value,
            "payload": {"source": "input.png", "target": "output.png"},
            "max_retries": 3,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_create_and_get_job_happy_path(client: TestClient) -> None:
    job_id = _create_job(client)

    response = client.get(f"/jobs/{job_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == job_id
    assert payload["status"] == Status.PENDING.value
    assert payload["retry_count"] == 0


def test_get_missing_job_returns_404(client: TestClient) -> None:
    response = client.get(f"/jobs/{uuid4()}")

    assert response.status_code == 404
    assert "detail" in response.json()


def test_delete_pending_job_returns_204_and_removes_job(client: TestClient) -> None:
    job_id = _create_job(client)

    delete_response = client.delete(f"/jobs/{job_id}")
    get_response = client.get(f"/jobs/{job_id}")

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


def test_delete_non_pending_job_returns_409(client: TestClient, db_engine) -> None:
    job_id = _create_job(client)

    with Session(db_engine) as session:
        job = session.exec(select(Job).where(Job.id == UUID(job_id))).one()
        job.status = Status.PROCESSING
        session.add(job)
        session.commit()

    response = client.delete(f"/jobs/{job_id}")

    assert response.status_code == 409
    assert "detail" in response.json()


def test_metrics_returns_expected_aggregates(client: TestClient, db_engine) -> None:
    first_id = _create_job(client)
    second_id = _create_job(client)

    with Session(db_engine) as session:
        first = session.exec(select(Job).where(Job.id == UUID(first_id))).one()
        second = session.exec(select(Job).where(Job.id == UUID(second_id))).one()

        first.status = Status.COMPLETED
        first.processing_duration_seconds = 4.0

        second.status = Status.FAILED
        second.processing_duration_seconds = 1.0

        session.add(first)
        session.add(second)
        session.commit()

    response = client.get("/metrics")

    assert response.status_code == 200
    body = response.json()
    assert body["total_jobs"] == 2
    assert body["pending_jobs"] == 0
    assert body["processing_jobs"] == 0
    assert body["completed_jobs"] == 1
    assert body["failed_jobs"] == 1
    assert body["average_processing_duration_seconds"] == 4.0


def test_empty_payload_is_rejected_with_422(client: TestClient) -> None:
    response = client.post(
        "/jobs",
        json={"job_type": JobType.REPORT_GENERATION.value, "payload": {}},
    )

    assert response.status_code == 422
    assert "detail" in response.json()
