import os
import time

import httpx
import pytest

pytestmark = pytest.mark.e2e

def _wait_for_api(base_url: str, timeout_seconds: int = 120) -> None:
    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        try:
            response = httpx.get(f"{base_url}/jobs/", params={"limit": 1}, timeout=3.0)
            if response.status_code == 200:
                return
            last_error = f"status={response.status_code} body={response.text}"
        except Exception as error:  # noqa: BLE001
            last_error = str(error)
        time.sleep(1)
    pytest.fail(f"API did not become ready within {timeout_seconds}s. Last error: {last_error}")


@pytest.fixture(scope="module")
def base_url() -> str:
    value = os.getenv("BASE_URL")
    if not value:
        pytest.skip("BASE_URL not set. Run this test via docker-compose.e2e test service.")
    return value.rstrip("/")


def test_job_is_processed_by_worker_e2e(base_url: str) -> None:
    _wait_for_api(base_url)

    create_response = httpx.post(
        f"{base_url}/jobs/",
        json={
            "job_type": "image_resize",
            "payload": {"source": "in.png", "target": "out.png"},
            "max_retries": 3,
        },
        timeout=5.0,
    )
    assert create_response.status_code == 201
    job_id = create_response.json()["id"]

    deadline = time.time() + 120
    last_payload = None

    while time.time() < deadline:
        get_response = httpx.get(f"{base_url}/jobs/{job_id}", timeout=5.0)
        assert get_response.status_code == 200
        last_payload = get_response.json()

        if last_payload["status"] in {"completed", "failed"}:
            break

        time.sleep(1)

    assert last_payload is not None
    assert last_payload["status"] in {"completed", "failed"}
    assert last_payload["started_at"] is not None
    if last_payload["status"] == "completed":
        assert last_payload["result"] is not None
