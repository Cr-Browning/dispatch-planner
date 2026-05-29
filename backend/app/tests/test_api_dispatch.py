"""Dispatch API integration tests (Phase 15)."""

from pathlib import Path

import pytest


def _create_run(client, auth_headers, seed_catalog, job_keys: list[str], name: str = "API Test") -> int:
    job_ids = [seed_catalog["jobs"][k].id for k in job_keys]
    response = client.post(
        "/dispatch-runs",
        json={"run_date": "2026-06-15", "name": name, "job_ids": job_ids},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.phase15
def test_dispatch_crud_and_auth(client, auth_headers, seed_catalog) -> None:
    empty = client.get("/dispatch-runs", headers=auth_headers)
    assert empty.status_code == 200
    assert empty.json() == []

    run_id = _create_run(
        client,
        auth_headers,
        seed_catalog,
        ["demo_cleaning"],
        name="CRUD Run",
    )
    get_one = client.get(f"/dispatch-runs/{run_id}", headers=auth_headers)
    assert get_one.status_code == 200
    assert get_one.json()["name"] == "CRUD Run"
    assert seed_catalog["jobs"]["demo_cleaning"].id in get_one.json()["job_ids"]

    listed = client.get("/dispatch-runs", headers=auth_headers)
    assert any(r["id"] == run_id for r in listed.json())

    no_auth = client.get("/dispatch-runs")
    assert no_auth.status_code == 401


@pytest.mark.phase15
def test_solve_and_plan(seed_catalog, client, auth_headers) -> None:
    run_id = _create_run(
        client,
        auth_headers,
        seed_catalog,
        ["demo_cleaning", "flooring_tile"],
        name="Solve Plan",
    )
    solve = client.post(f"/dispatch-runs/{run_id}/solve", headers=auth_headers)
    assert solve.status_code == 200
    solved = solve.json()
    assert solved["dispatch_run_id"] == run_id
    assert len(solved["assignments"]) >= 6
    assert len(solved["vehicle_routes"]) >= 1
    assert solved["reasoning_summary"]

    plan = client.get(f"/dispatch-runs/{run_id}/plan", headers=auth_headers)
    assert plan.status_code == 200
    planned = plan.json()
    assert len(planned["assignments"]) == len(solved["assignments"])
    assert len(planned["vehicle_routes"]) == len(solved["vehicle_routes"])
    route = planned["vehicle_routes"][0]
    assert route.get("route_geometry_json") is not None
    assert any(s.get("latitude") is not None for s in route["stops"])


@pytest.mark.phase15
def test_recalculate_after_solve(seed_catalog, client, auth_headers) -> None:
    run_id = _create_run(
        client,
        auth_headers,
        seed_catalog,
        ["demo_cleaning", "flooring_tile"],
    )
    client.post(f"/dispatch-runs/{run_id}/solve", headers=auth_headers)
    response = client.post(f"/dispatch-runs/{run_id}/recalculate", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["dispatch_run_id"] == run_id
    assert len(body["vehicle_routes"]) >= 1
    assert isinstance(body["warnings"], list)


@pytest.mark.phase15
def test_quality_bar_end_to_end(
    seed_catalog, client, auth_headers, tmp_export_dir
) -> None:
    """Covers product quality bar: seed → two jobs → solve → routes → edit → recalc → CSV."""
    # 1–2: seed fixture + two jobs for one day
    run_id = _create_run(
        client,
        auth_headers,
        seed_catalog,
        ["demo_cleaning", "flooring_tile"],
        name="Quality Bar Run",
    )

    # 3–8: assign, vehicles, scarcity signals, pickups, ETA/mileage, reasoning
    solve = client.post(f"/dispatch-runs/{run_id}/solve", headers=auth_headers)
    assert solve.status_code == 200
    body = solve.json()
    assignments = body["assignments"]
    routes = body["vehicle_routes"]
    assert len(assignments) >= 6
    assert len(routes) >= 1

    drivers = [a for a in assignments if a["assigned_role"] == "driver"]
    assert drivers
    assert len(routes) <= len(drivers)

    cleaning_id = seed_catalog["jobs"]["demo_cleaning"].id
    cleaning_count = sum(1 for a in assignments if a["job_id"] == cleaning_id)
    assert cleaning_count >= seed_catalog["jobs"]["demo_cleaning"].required_headcount

    assert body["reasoning_summary"]
    assert body["route_reasoning_summary"] or any(r.get("reasoning") for r in routes)

    for route in routes:
        assert route["total_duration_minutes"] is not None
        assert route["total_distance_miles"] is not None
        assert len(route["stops"]) >= 2
        assert any(s.get("eta") for s in route["stops"])
        if route.get("google_maps_url"):
            assert route["google_maps_url"].startswith("http")

    # 9: manual edit
    employee_id = assignments[0]["employee_id"]
    tile_job_id = seed_catalog["jobs"]["flooring_tile"].id
    override = client.post(
        f"/dispatch-runs/{run_id}/manual-override",
        json={
            "move_assignment": {
                "employee_id": employee_id,
                "to_job_id": tile_job_id,
                "assigned_role": "worker",
            }
        },
        headers=auth_headers,
    )
    assert override.status_code == 200
    updated = next(a for a in override.json()["assignments"] if a["employee_id"] == employee_id)
    assert updated["job_id"] == tile_job_id
    assert updated["manually_overridden"] is True

    # 10: recalculate warnings/routes after edit
    recalc = client.post(f"/dispatch-runs/{run_id}/recalculate", headers=auth_headers)
    assert recalc.status_code == 200
    assert len(recalc.json()["vehicle_routes"]) >= 1

    # 11: CSV export
    export = client.post(f"/dispatch-runs/{run_id}/export-csv", headers=auth_headers)
    assert export.status_code == 200
    export_body = export.json()
    assert export_body["row_count"] >= 4
    assert Path(export_body["file_path"]).is_file()
