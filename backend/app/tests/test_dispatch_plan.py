"""Dispatch plan API tests (Phase 14 — geometry exposed to map preview)."""

import pytest


def _solve_run(seed_catalog, client, auth_headers, job_keys: list[str]) -> int:
    job_ids = [seed_catalog["jobs"][k].id for k in job_keys]
    create = client.post(
        "/dispatch-runs",
        json={"run_date": "2026-06-15", "name": "Plan Map Test", "job_ids": job_ids},
        headers=auth_headers,
    )
    assert create.status_code == 201
    run_id = create.json()["id"]
    solve = client.post(f"/dispatch-runs/{run_id}/solve", headers=auth_headers)
    assert solve.status_code == 200
    return run_id


@pytest.mark.phase14
def test_plan_includes_geometry_and_stop_coordinates(
    seed_catalog, client, auth_headers
) -> None:
    run_id = _solve_run(
        seed_catalog,
        client,
        auth_headers,
        ["demo_cleaning"],
    )
    response = client.get(f"/dispatch-runs/{run_id}/plan", headers=auth_headers)
    assert response.status_code == 200
    routes = response.json()["vehicle_routes"]
    assert len(routes) >= 1
    route = routes[0]
    assert "route_geometry_json" in route
    assert route["route_geometry_json"] is not None
    assert len(route["stops"]) >= 2
    with_coords = [s for s in route["stops"] if s.get("latitude") is not None]
    assert len(with_coords) >= 2
