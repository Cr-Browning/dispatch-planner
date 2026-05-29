"""Job API tests (Phase 4)."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient


@pytest.mark.phase4
def test_job_full_flow(client: TestClient, auth_headers: dict) -> None:
    cleaning = client.post("/skills", json={"name": "Cleaning"}, headers=auth_headers).json()
    contents = client.post("/skills", json={"name": "Contents"}, headers=auth_headers).json()
    employee = client.post(
        "/employees",
        json={"first_name": "Chris", "last_name": "Cleaner"},
        headers=auth_headers,
    ).json()

    arrival = datetime(2026, 6, 1, 8, 0, tzinfo=UTC).isoformat()
    create = client.post(
        "/jobs",
        json={
            "job_name": "Cleaning Job",
            "address": "500 Oak Ave",
            "required_arrival_time": arrival,
            "required_headcount": 2,
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    job_id = create.json()["id"]

    req = client.post(
        f"/jobs/{job_id}/required-skills",
        json={
            "skill_id": cleaning["id"],
            "required_quantity": 1,
            "minimum_proficiency": 3,
            "is_preferred": False,
        },
        headers=auth_headers,
    )
    assert req.status_code == 201
    assert req.json()["skill_name"] == "Cleaning"
    sub = client.post(
        f"/jobs/{job_id}/manual-substitutions",
        json={
            "required_skill_id": cleaning["id"],
            "substitute_skill_id": contents["id"],
            "allowed": True,
        },
        headers=auth_headers,
    )
    assert sub.status_code == 201

    inc = client.post(
        f"/jobs/{job_id}/include-employee",
        json={"employee_id": employee["id"]},
        headers=auth_headers,
    )
    assert inc.status_code == 201

    exc = client.post(
        f"/jobs/{job_id}/exclude-employee",
        json={"employee_id": employee["id"]},
        headers=auth_headers,
    )
    assert exc.status_code == 201

    detail = client.get(f"/jobs/{job_id}", headers=auth_headers)
    assert detail.status_code == 200
    data = detail.json()
    assert len(data["required_skills"]) == 1
    assert len(data["manual_substitutions"]) == 1
    assert len(data["included_employees"]) == 1
    assert len(data["excluded_employees"]) == 1


@pytest.mark.phase4
def test_delete_required_skill(client: TestClient, auth_headers: dict) -> None:
    cleaning = client.post("/skills", json={"name": "Cleaning2"}, headers=auth_headers).json()
    arrival = datetime(2026, 6, 1, 8, 0, tzinfo=UTC).isoformat()
    job_id = client.post(
        "/jobs",
        json={
            "address": "9 Main St",
            "required_arrival_time": arrival,
            "required_headcount": 1,
        },
        headers=auth_headers,
    ).json()["id"]
    req = client.post(
        f"/jobs/{job_id}/required-skills",
        json={"skill_id": cleaning["id"], "required_quantity": 1, "minimum_proficiency": 1},
        headers=auth_headers,
    )
    required_skill_id = req.json()["id"]
    assert (
        client.delete(
            f"/jobs/{job_id}/required-skills/{required_skill_id}",
            headers=auth_headers,
        ).status_code
        == 204
    )
    detail = client.get(f"/jobs/{job_id}", headers=auth_headers).json()
    assert detail["required_skills"] == []


@pytest.mark.phase4
def test_job_create_geocodes_address(client: TestClient, auth_headers: dict) -> None:
    arrival = datetime(2026, 6, 1, 8, 0, tzinfo=UTC).isoformat()
    response = client.post(
        "/jobs",
        json={
            "address": "100 Market St, Philadelphia, PA",
            "required_arrival_time": arrival,
            "required_headcount": 1,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["latitude"] is not None
    assert data["longitude"] is not None


@pytest.mark.phase4
def test_get_missing_job_returns_404(client: TestClient, auth_headers: dict) -> None:
    assert client.get("/jobs/99999", headers=auth_headers).status_code == 404


@pytest.mark.phase15
def test_delete_job_used_in_dispatch_run(
    client: TestClient, auth_headers: dict, seed_catalog
) -> None:
    job_id = seed_catalog["jobs"]["demo_cleaning"].id
    run_id = client.post(
        "/dispatch-runs",
        json={
            "run_date": "2026-06-15",
            "name": "Delete job test",
            "job_ids": [job_id, seed_catalog["jobs"]["flooring_tile"].id],
        },
        headers=auth_headers,
    ).json()["id"]
    client.post(f"/dispatch-runs/{run_id}/solve", headers=auth_headers)
    assert client.delete(f"/jobs/{job_id}", headers=auth_headers).status_code == 204
    assert client.get(f"/jobs/{job_id}", headers=auth_headers).status_code == 404


@pytest.mark.phase4
def test_delete_job(client: TestClient, auth_headers: dict) -> None:
    arrival = datetime(2026, 6, 1, 8, 0, tzinfo=UTC).isoformat()
    job = client.post(
        "/jobs",
        json={"address": "1 St", "required_arrival_time": arrival, "required_headcount": 1},
        headers=auth_headers,
    ).json()
    assert client.delete(f"/jobs/{job['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/jobs/{job['id']}", headers=auth_headers).status_code == 404


@pytest.mark.phase4
def test_job_missing_address_validation(client: TestClient, auth_headers: dict) -> None:
    arrival = datetime(2026, 6, 1, 8, 0, tzinfo=UTC).isoformat()
    response = client.post(
        "/jobs",
        json={"required_arrival_time": arrival, "required_headcount": 1},
        headers=auth_headers,
    )
    assert response.status_code == 422
