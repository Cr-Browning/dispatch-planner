"""Pytest fixtures — shared across all phases."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

# Must set env before app modules create the engine
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("DISPATCHER_PASSWORD", "testpass")
os.environ.setdefault("BACKUP_ON_STARTUP", "false")

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.core.database import SessionLocal, init_db, reset_db_for_tests  # noqa: E402
from app.main import app  # noqa: E402
from app.routing.mock_provider import MockRoutingProvider  # noqa: E402
from app.seed.seed_data import seed_database  # noqa: E402
from app.services.eligibility_service import EligibilityService  # noqa: E402
from app.services.route_matrix_service import RouteMatrixService  # noqa: E402
from app.services.scarcity_service import ScarcityService  # noqa: E402
from app.tests import factories  # noqa: E402

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models import Employee, Job, Skill


@pytest.fixture(autouse=True)
def _fresh_db():
    reset_db_for_tests()
    init_db()
    yield


@pytest.fixture
def db_session() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(_fresh_db) -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/auth/login", json={"password": "testpass"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def skill_factory(db_session: Session) -> Callable[..., Skill]:
    def _create(**kwargs) -> Skill:
        skill = factories.create_skill(db_session, **kwargs)
        db_session.commit()
        return skill

    return _create


@pytest.fixture
def employee_factory(db_session: Session) -> Callable[..., Employee]:
    def _create(**kwargs) -> Employee:
        employee = factories.create_employee(db_session, **kwargs)
        db_session.commit()
        return employee

    return _create


@pytest.fixture
def job_factory(db_session: Session) -> Callable[..., Job]:
    def _create(**kwargs) -> Job:
        job = factories.create_job(db_session, **kwargs)
        db_session.commit()
        return job

    return _create


@pytest.fixture
def mock_routing_provider() -> MockRoutingProvider:
    return MockRoutingProvider()


@pytest.fixture
def route_matrix_service(db_session: Session, mock_routing_provider: MockRoutingProvider) -> RouteMatrixService:
    return RouteMatrixService(db_session, mock_routing_provider)


@pytest.fixture
def eligibility_service(db_session: Session) -> EligibilityService:
    return EligibilityService(db_session)


@pytest.fixture
def scarcity_service(db_session: Session) -> ScarcityService:
    return ScarcityService(db_session)


@pytest.fixture
def tmp_export_dir(tmp_path, monkeypatch):
    """Isolated export directory for Phase 12+ tests."""
    export_path = tmp_path / "exports"
    export_path.mkdir()
    monkeypatch.setenv("EXPORT_DIR", str(export_path))
    get_settings.cache_clear()
    yield export_path
    get_settings.cache_clear()


@pytest.fixture
def seed_catalog(db_session: Session) -> dict:
    """Full product seed dataset (Phase 5) for solver and integration tests."""
    catalog = seed_database(db_session, commit=True)
    return {
        "skills": catalog.skills,
        "employees": catalog.employees,
        "jobs": catalog.jobs,
        "profiles": catalog.profiles,
    }
