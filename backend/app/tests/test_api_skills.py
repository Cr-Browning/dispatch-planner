"""Skill API tests (Phase 4)."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.phase4
def test_list_skills_empty(client: TestClient, auth_headers: dict) -> None:
    response = client.get("/skills", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.phase4
def test_create_and_update_skill(client: TestClient, auth_headers: dict) -> None:
    create = client.post("/skills", json={"name": "Demo", "active": True}, headers=auth_headers)
    assert create.status_code == 201
    body = create.json()
    assert body["name"] == "Demo"
    assert "id" in body
    assert "created_at" in body

    update = client.put(
        f"/skills/{body['id']}",
        json={"active": False},
        headers=auth_headers,
    )
    assert update.status_code == 200
    assert update.json()["active"] is False


@pytest.mark.phase4
def test_duplicate_skill_returns_409(client: TestClient, auth_headers: dict) -> None:
    client.post("/skills", json={"name": "Framing"}, headers=auth_headers)
    dup = client.post("/skills", json={"name": "Framing"}, headers=auth_headers)
    assert dup.status_code == 409


@pytest.mark.phase4
def test_create_skill_validation_error(client: TestClient, auth_headers: dict) -> None:
    response = client.post("/skills", json={"name": ""}, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.phase4
def test_update_missing_skill_returns_404(client: TestClient, auth_headers: dict) -> None:
    response = client.put("/skills/99999", json={"active": False}, headers=auth_headers)
    assert response.status_code == 404
