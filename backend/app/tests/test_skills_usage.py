"""Skills list with usage counts."""

import pytest


@pytest.mark.phase15
def test_list_skills_with_usage(seed_catalog, client, auth_headers) -> None:
    response = client.get("/skills?with_usage=true", headers=auth_headers)
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) >= 1
    assert "job_usage_count" in rows[0]
    assert "employee_usage_count" in rows[0]
    assert any(r["job_usage_count"] > 0 for r in rows)
