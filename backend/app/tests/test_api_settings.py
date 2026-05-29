"""Settings API tests (Phase 13)."""

import pytest


@pytest.mark.phase13
def test_get_settings(client, auth_headers, seed_catalog) -> None:
    response = client.get("/settings", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["routing_provider"] in ("mock", "google")
    assert "Date" in data["export_columns"]
    assert "Job Name" in data["export_columns"]


@pytest.mark.phase13
def test_update_settings_returns_current(client, auth_headers) -> None:
    response = client.put("/settings", json={}, headers=auth_headers)
    assert response.status_code == 200
    assert "export_columns" in response.json()
