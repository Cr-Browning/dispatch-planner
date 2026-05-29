"""Employee API tests (Phase 4)."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.phase4
def test_employee_full_flow(client: TestClient, auth_headers: dict) -> None:
    skill = client.post("/skills", json={"name": "Tile"}, headers=auth_headers).json()

    create = client.post(
        "/employees",
        json={
            "first_name": "Taylor",
            "last_name": "Tile",
            "is_driver": False,
            "is_supervisor": False,
            "default_vehicle_capacity": 4,
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    employee_id = create.json()["id"]

    loc = client.post(
        f"/employees/{employee_id}/locations",
        json={
            "label": "Home",
            "address": "123 Main St",
            "latitude": 40.0,
            "longitude": -75.0,
            "is_primary": True,
        },
        headers=auth_headers,
    )
    assert loc.status_code == 201

    eskill = client.post(
        f"/employees/{employee_id}/skills",
        json={"skill_id": skill["id"], "proficiency": 5},
        headers=auth_headers,
    )
    assert eskill.status_code == 201
    assert eskill.json()["skill_name"] == "Tile"

    detail = client.get(f"/employees/{employee_id}", headers=auth_headers)
    assert detail.status_code == 200
    data = detail.json()
    assert len(data["locations"]) == 1
    assert len(data["skills"]) == 1

    delete = client.delete(f"/employees/{employee_id}", headers=auth_headers)
    assert delete.status_code == 204


@pytest.mark.phase4
def test_remove_employee_skill(client: TestClient, auth_headers: dict) -> None:
    skill = client.post("/skills", json={"name": "Mitigation"}, headers=auth_headers).json()
    employee = client.post(
        "/employees",
        json={"first_name": "Sam", "last_name": "Tech"},
        headers=auth_headers,
    ).json()
    employee_id = employee["id"]
    client.post(
        f"/employees/{employee_id}/skills",
        json={"skill_id": skill["id"], "proficiency": 4},
        headers=auth_headers,
    )
    assert (
        client.delete(
            f"/employees/{employee_id}/skills/{skill['id']}", headers=auth_headers
        ).status_code
        == 204
    )
    detail = client.get(f"/employees/{employee_id}", headers=auth_headers).json()
    assert detail["skills"] == []


@pytest.mark.phase4
def test_get_missing_employee_returns_404(client: TestClient, auth_headers: dict) -> None:
    response = client.get("/employees/99999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.phase4
def test_duplicate_employee_skill_returns_409(client: TestClient, auth_headers: dict) -> None:
    skill = client.post("/skills", json={"name": "Demo"}, headers=auth_headers).json()
    employee = client.post(
        "/employees",
        json={"first_name": "A", "last_name": "B"},
        headers=auth_headers,
    ).json()
    payload = {"skill_id": skill["id"], "proficiency": 3}
    assert client.post(
        f"/employees/{employee['id']}/skills", json=payload, headers=auth_headers
    ).status_code == 201
    dup = client.post(
        f"/employees/{employee['id']}/skills", json=payload, headers=auth_headers
    )
    assert dup.status_code == 409


@pytest.mark.phase4
def test_invalid_proficiency_returns_422(client: TestClient, auth_headers: dict) -> None:
    skill = client.post("/skills", json={"name": "HVAC"}, headers=auth_headers).json()
    employee = client.post(
        "/employees",
        json={"first_name": "A", "last_name": "B"},
        headers=auth_headers,
    ).json()
    response = client.post(
        f"/employees/{employee['id']}/skills",
        json={"skill_id": skill["id"], "proficiency": 9},
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.phase4
def test_update_location(client: TestClient, auth_headers: dict) -> None:
    employee = client.post(
        "/employees",
        json={"first_name": "A", "last_name": "B"},
        headers=auth_headers,
    ).json()
    loc = client.post(
        f"/employees/{employee['id']}/locations",
        json={"label": "Home", "address": "1 A St", "is_primary": True},
        headers=auth_headers,
    ).json()
    update = client.put(
        f"/employees/{employee['id']}/locations/{loc['id']}",
        json={"label": "Hotel", "is_primary": False},
        headers=auth_headers,
    )
    assert update.status_code == 200
    assert update.json()["label"] == "Hotel"


@pytest.mark.phase4
def test_active_only_filter(client: TestClient, auth_headers: dict) -> None:
    client.post(
        "/employees",
        json={"first_name": "Active", "last_name": "One", "active": True},
        headers=auth_headers,
    )
    client.post(
        "/employees",
        json={"first_name": "Inactive", "last_name": "Two", "active": False},
        headers=auth_headers,
    )
    all_resp = client.get("/employees", headers=auth_headers)
    active_resp = client.get("/employees?active_only=true", headers=auth_headers)
    assert len(all_resp.json()) == 2
    assert len(active_resp.json()) == 1
    assert active_resp.json()[0]["first_name"] == "Active"
