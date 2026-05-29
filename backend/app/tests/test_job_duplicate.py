"""Job duplicate API tests."""

import pytest


@pytest.mark.phase15
def test_duplicate_job_copies_roles(seed_catalog, client, auth_headers) -> None:
    source = seed_catalog["jobs"]["demo_cleaning"]
    response = client.post(
        f"/jobs/{source.id}/duplicate",
        json={"run_date": "2026-06-16"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    copy = response.json()
    assert copy["id"] != source.id
    assert "(copy)" in (copy["job_name"] or "")
    source_detail = client.get(f"/jobs/{source.id}", headers=auth_headers).json()
    assert len(copy["required_skills"]) == len(source_detail["required_skills"])
    assert copy["required_arrival_time"].startswith("2026-06-16")
