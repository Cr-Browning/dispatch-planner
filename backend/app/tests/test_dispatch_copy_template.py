"""Dispatch copy-template API tests."""

import pytest


@pytest.mark.phase15
def test_copy_template_returns_latest_run_jobs(
    seed_catalog, client, auth_headers
) -> None:
    job_ids = [
        seed_catalog["jobs"]["demo_cleaning"].id,
        seed_catalog["jobs"]["flooring_tile"].id,
    ]
    create = client.post(
        "/dispatch-runs",
        json={"run_date": "2026-06-14", "name": "Yesterday", "job_ids": job_ids},
        headers=auth_headers,
    )
    assert create.status_code == 201

    response = client.get(
        "/dispatch-runs/copy-template?target_run_date=2026-06-15",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert set(data["job_ids"]) == set(job_ids)
    assert data["source_run_name"] == "Yesterday"
    assert data["suggested_name"].startswith("Dispatch —")
    assert "jobs_on_run_date_count" in data
    assert data["jobs_on_run_date_count"] == 2


@pytest.mark.phase15
def test_copy_template_empty_when_no_runs(client, auth_headers) -> None:
    response = client.get("/dispatch-runs/copy-template", headers=auth_headers)
    assert response.status_code == 400
