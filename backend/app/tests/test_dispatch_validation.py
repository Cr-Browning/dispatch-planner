"""Pre-solve validation API tests."""

import pytest


@pytest.mark.phase15
def test_validate_ready_run(seed_catalog, client, auth_headers) -> None:
    job_ids = [
        seed_catalog["jobs"]["demo_cleaning"].id,
        seed_catalog["jobs"]["flooring_tile"].id,
    ]
    response = client.post(
        "/dispatch-runs/validate",
        json={"run_date": "2026-06-15", "job_ids": job_ids},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is True
    assert not any(i["level"] == "error" for i in body["issues"])


@pytest.mark.phase15
def test_validate_empty_selection(client, auth_headers) -> None:
    response = client.post(
        "/dispatch-runs/validate",
        json={"run_date": "2026-06-15", "job_ids": []},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is False
    assert any("Select at least one" in i["message"] for i in body["issues"])


@pytest.mark.phase15
def test_validate_requires_auth(client) -> None:
    response = client.post(
        "/dispatch-runs/validate",
        json={"run_date": "2026-06-15", "job_ids": [1]},
    )
    assert response.status_code == 401
