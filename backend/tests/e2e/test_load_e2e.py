import os
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.load]


def _get_int_env(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, value)


def _wait_for_api(base_url: str, timeout_seconds: int = 120) -> None:
    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        try:
            response = httpx.get(f"{base_url}/jobs", params={"limit": 1}, timeout=3.0)
            if response.status_code == 200:
                return
            last_error = f"status={response.status_code} body={response.text}"
        except Exception as error:  # noqa: BLE001
            last_error = str(error)
        time.sleep(1)
    pytest.fail(
        f"API did not become ready within {timeout_seconds}s. Last error: {last_error}"
    )


@pytest.fixture(scope="module")
def base_url() -> str:
    value = os.getenv("BASE_URL")
    if not value:
        pytest.skip(
            "BASE_URL not set. Run this test via docker-compose.load load_test service."
        )
    return value.rstrip("/")


def test_job_submission_and_processing_under_load(base_url: str) -> None:
    _wait_for_api(base_url)

    total_requests = _get_int_env("LOAD_REQUESTS", 500)
    concurrency = _get_int_env("LOAD_CONCURRENCY", 50)
    timeout_seconds = _get_int_env("LOAD_TIMEOUT_SECONDS", 300)

    def _create_job(_index: int) -> tuple[int, str | None, str]:
        response = httpx.post(
            f"{base_url}/jobs",
            json={
                "job_type": "image_resize",
                "payload": {"source": "in.png", "target": "out.png", "seq": _index},
                "max_retries": 3,
            },
            timeout=10.0,
        )

        job_id = None
        if response.status_code == 201:
            try:
                job_id = response.json().get("id")
            except Exception:  # noqa: BLE001
                job_id = None

        return response.status_code, job_id, response.text

    started_at = time.time()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        results = list(executor.map(_create_job, range(total_requests)))

    duration_create = time.time() - started_at

    failed_creates = [
        {"status": status, "body": body}
        for (status, _job_id, body) in results
        if status != 201
    ]
    assert not failed_creates, f"Create requests failed: {failed_creates[:5]}"

    created_job_ids = [
        job_id for (_status, job_id, _body) in results if job_id is not None
    ]
    assert len(created_job_ids) == total_requests, (
        f"Expected {total_requests} created jobs, got {len(created_job_ids)}"
    )

    deadline = time.time() + timeout_seconds
    last_metrics = None
    while time.time() < deadline:
        metrics_response = httpx.get(f"{base_url}/metrics", timeout=5.0)
        assert metrics_response.status_code == 200
        last_metrics = metrics_response.json()

        finished_jobs = int(last_metrics["completed_jobs"]) + int(
            last_metrics["failed_jobs"]
        )
        if finished_jobs >= total_requests:
            break

        time.sleep(1)

    assert last_metrics is not None
    finished_jobs = int(last_metrics["completed_jobs"]) + int(
        last_metrics["failed_jobs"]
    )

    assert finished_jobs >= total_requests, (
        "Timeout waiting for all jobs to reach terminal state. "
        f"finished={finished_jobs}, expected={total_requests}, metrics={last_metrics}"
    )

    completed_jobs = int(last_metrics["completed_jobs"])
    failed_jobs = int(last_metrics["failed_jobs"])
    total_time = time.time() - started_at
    print(
        "LOAD SUMMARY "
        f"submitted={total_requests} "
        f"concurrency={concurrency} "
        f"finished={finished_jobs} "
        f"completed={completed_jobs} "
        f"failed={failed_jobs} "
        f"create_seconds={duration_create:.2f} "
        f"total_seconds={total_time:.2f}"
    )
