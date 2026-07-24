from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, delete

from app.db.models import Job
from app.db.session import get_session
from app.main import app

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture
def db_engine():
    return test_engine


def _override_get_session() -> Generator[Session, None, None]:
    with Session(test_engine) as session:
        yield session


@pytest.fixture(autouse=True)
def _reset_jobs_table() -> Generator[None, None, None]:
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        session.exec(delete(Job))
        session.commit()
    yield


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    # Prevent startup from touching the production/Postgres engine during tests.
    monkeypatch.setattr("app.main.create_db_and_tables", lambda: SQLModel.metadata.create_all(test_engine))
    app.dependency_overrides[get_session] = _override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
