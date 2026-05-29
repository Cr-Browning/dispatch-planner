"""Authentication endpoint tests."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.phase3
def test_login_success(client: TestClient) -> None:
    response = client.post("/auth/login", json={"password": "testpass"})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 10


@pytest.mark.phase3
def test_login_failure(client: TestClient) -> None:
    response = client.post("/auth/login", json={"password": "wrong"})
    assert response.status_code == 401


@pytest.mark.phase3
def test_me_requires_auth(client: TestClient) -> None:
    response = client.get("/auth/me")
    assert response.status_code == 401


@pytest.mark.phase3
def test_me_with_token(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["username"] == "dispatcher"
    assert response.json()["role"] == "dispatcher"


@pytest.mark.phase3
def test_protected_route_requires_auth(client: TestClient) -> None:
    response = client.get("/employees")
    assert response.status_code == 401


@pytest.mark.phase3
def test_protected_route_with_auth(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/employees", headers=auth_headers)
    assert response.status_code == 200
