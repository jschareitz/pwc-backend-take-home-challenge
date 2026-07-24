from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import get_job_service
from app.core.exceptions import JobAlreadyStartedException, JobNotFoundException
from app.main import app
from app.schemas.jobs import JobType

pytestmark = pytest.mark.api


class _RaisingJobService:
    def get_job(self, _job_id):
        raise JobNotFoundException(uuid4())

    def delete_job(self, _job_id):
        raise JobAlreadyStartedException(uuid4())

    def create_job(self, _data):
        raise SQLAlchemyError("simulated db failure")


def test_create_job_rejects_out_of_range_retries(client: TestClient) -> None:
    response = client.post(
        "/jobs/",
        json={
            "job_type": JobType.DATA_IMPORT.value,
            "payload": {"file": "import.csv"},
            "max_retries": 99,
        },
    )

    assert response.status_code == 422
    assert "detail" in response.json()


def test_get_job_with_invalid_uuid_returns_422(client: TestClient) -> None:
    response = client.get("/jobs/not-a-uuid")

    assert response.status_code == 422
    assert "detail" in response.json()


def test_route_maps_job_not_found_to_404(client: TestClient) -> None:
    app.dependency_overrides[get_job_service] = lambda: _RaisingJobService()
    try:
        response = client.get(f"/jobs/{uuid4()}")
    finally:
        app.dependency_overrides.pop(get_job_service, None)

    assert response.status_code == 404
    assert "detail" in response.json()


def test_route_maps_already_started_delete_to_409(client: TestClient) -> None:
    app.dependency_overrides[get_job_service] = lambda: _RaisingJobService()
    try:
        response = client.delete(f"/jobs/{uuid4()}")
    finally:
        app.dependency_overrides.pop(get_job_service, None)

    assert response.status_code == 409
    assert "detail" in response.json()


def test_route_maps_sqlalchemy_error_to_500(client: TestClient) -> None:
    app.dependency_overrides[get_job_service] = lambda: _RaisingJobService()
    try:
        response = client.post(
            "/jobs/",
            json={
                "job_type": JobType.IMAGE_RESIZE.value,
                "payload": {"source": "a.png", "target": "b.png"},
            },
        )
    finally:
        app.dependency_overrides.pop(get_job_service, None)

    assert response.status_code == 500
    assert response.json() == {"detail": "Database error"}
