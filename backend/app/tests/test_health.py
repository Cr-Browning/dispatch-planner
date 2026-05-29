"""Health endpoint tests."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.phase3
def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["schema_version"] == "1"
