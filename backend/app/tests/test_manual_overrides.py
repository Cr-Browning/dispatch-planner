"""Manual override and recalculate tests (Phase 11)."""

import pytest

from app.schemas.manual_override import (
    ManualOverrideRequest,
    MoveAssignmentAction,
    MoveToVehicleAction,
    ReorderPickupsAction,
)
from app.services.manual_override_service import ManualOverrideService


def _solve_run(seed_catalog, db_session, client, auth_headers, job_keys: list[str]) -> int:
    job_ids = [seed_catalog["jobs"][k].id for k in job_keys]
    create = client.post(
        "/dispatch-runs",
        json={"run_date": "2026-06-15", "name": "Override Test", "job_ids": job_ids},
        headers=auth_headers,
    )
    assert create.status_code == 201
    run_id = create.json()["id"]
    solve = client.post(f"/dispatch-runs/{run_id}/solve", headers=auth_headers)
    assert solve.status_code == 200
    return run_id


@pytest.fixture
def override_service(db_session, route_matrix_service) -> ManualOverrideService:
    from app.services.route_planning_service import RoutePlanningService

    planner = RoutePlanningService(db_session, route_matrix_service)
    return ManualOverrideService(db_session, planner)


@pytest.mark.phase11
def test_move_assignment_updates_job_and_flag(
    seed_catalog, db_session, client, auth_headers, override_service
) -> None:
    run_id = _solve_run(
        seed_catalog,
        db_session,
        client,
        auth_headers,
        ["demo_cleaning", "flooring_tile"],
    )
    taylor_id = seed_catalog["employees"]["taylor_tile"].id
    cleaning_id = seed_catalog["jobs"]["demo_cleaning"].id

    result = override_service.apply_override(
        run_id,
        ManualOverrideRequest(
            move_assignment=MoveAssignmentAction(
                employee_id=taylor_id,
                to_job_id=cleaning_id,
                assigned_role="worker",
            )
        ),
    )
    taylor = next(a for a in result.assignments if a.employee_id == taylor_id)
    assert taylor.job_id == cleaning_id
    assert taylor.manually_overridden is True
    assert result.override_type == "move_assignment"
    assert any("scarce" in w.lower() or "manual" in w.lower() for w in result.warnings)


@pytest.mark.phase11
def test_move_assignment_via_api(seed_catalog, db_session, client, auth_headers) -> None:
    job_ids = [
        seed_catalog["jobs"]["demo_cleaning"].id,
        seed_catalog["jobs"]["flooring_tile"].id,
    ]
    create = client.post(
        "/dispatch-runs",
        json={"run_date": "2026-06-15", "name": "API Override", "job_ids": job_ids},
        headers=auth_headers,
    )
    run_id = create.json()["id"]
    solve = client.post(f"/dispatch-runs/{run_id}/solve", headers=auth_headers)
    assert solve.status_code == 200
    assignments = solve.json()["assignments"]
    employee_id = assignments[0]["employee_id"]
    tile_job_id = seed_catalog["jobs"]["flooring_tile"].id

    response = client.post(
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
    assert response.status_code == 200
    body = response.json()
    updated = next(a for a in body["assignments"] if a["employee_id"] == employee_id)
    assert updated["job_id"] == tile_job_id
    assert updated["manually_overridden"] is True


@pytest.mark.phase11
def test_reorder_pickups_updates_stop_order(
    seed_catalog, db_session, client, auth_headers, override_service
) -> None:
    run_id = _solve_run(
        seed_catalog,
        db_session,
        client,
        auth_headers,
        ["mitigation_large"],
    )
    from app.models import DispatchRun
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models import DispatchVehicleRoute

    run = db_session.scalars(
        select(DispatchRun)
        .where(DispatchRun.id == run_id)
        .options(
            selectinload(DispatchRun.vehicle_routes).selectinload(
                DispatchVehicleRoute.stops
            )
        )
    ).first()
    route = next(r for r in run.vehicle_routes if len(_passenger_ids(r)) >= 2)
    passengers = _passenger_ids(route)
    reversed_order = list(reversed(passengers))

    result = override_service.apply_override(
        run_id,
        ManualOverrideRequest(
            reorder_pickups=ReorderPickupsAction(
                vehicle_route_id=route.id,
                pickup_employee_ids=reversed_order,
            )
        ),
    )
    updated = next(
        r for r in result.vehicle_routes if r.route_order == route.route_order
    )
    pickup_stops = [s for s in updated.stops if s.stop_type == "pickup"]
    assert [s.employee_id for s in pickup_stops] == reversed_order
    assert result.override_type == "reorder_pickups"
    assert all(s.eta is not None for s in updated.stops)


@pytest.mark.phase11
def test_move_to_vehicle_capacity_warning(
    seed_catalog, db_session, client, auth_headers, override_service
) -> None:
    run_id = _solve_run(
        seed_catalog,
        db_session,
        client,
        auth_headers,
        ["mitigation_large"],
    )
    from app.models import DispatchRun
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models import DispatchVehicleRoute

    run = db_session.scalars(
        select(DispatchRun)
        .where(DispatchRun.id == run_id)
        .options(
            selectinload(DispatchRun.vehicle_routes).selectinload(
                DispatchVehicleRoute.stops
            )
        )
    ).first()
    routes = sorted(run.vehicle_routes, key=lambda r: r.route_order)
    if len(routes) < 2:
        pytest.skip("Need at least two vehicle routes for this scenario")
    source = routes[0]
    target = routes[1]
    passenger_to_move = _passenger_ids(source)[0]

    result = override_service.apply_override(
        run_id,
        ManualOverrideRequest(
            move_to_vehicle=MoveToVehicleAction(
                employee_id=passenger_to_move,
                target_vehicle_route_id=target.id,
            )
        ),
    )
    assert result.override_type == "move_to_vehicle"
    assert any("manual" in w.lower() for w in result.warnings)
    moved = next(a for a in result.assignments if a.employee_id == passenger_to_move)
    assert moved.manually_overridden is True


@pytest.mark.phase11
def test_recalculate_refreshes_routes(
    seed_catalog, db_session, client, auth_headers, override_service
) -> None:
    run_id = _solve_run(
        seed_catalog,
        db_session,
        client,
        auth_headers,
        ["demo_cleaning", "flooring_tile"],
    )
    result = override_service.recalculate(run_id)
    assert result.override_type == "recalculate"
    assert len(result.vehicle_routes) >= 2
    assert all(r.google_maps_url for r in result.vehicle_routes)


@pytest.mark.phase11
def test_recalculate_via_api(seed_catalog, db_session, client, auth_headers) -> None:
    run_id = _solve_run(
        seed_catalog,
        db_session,
        client,
        auth_headers,
        ["demo_cleaning"],
    )
    response = client.post(
        f"/dispatch-runs/{run_id}/recalculate",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["override_type"] == "recalculate"
    assert len(response.json()["vehicle_routes"]) >= 1


def _passenger_ids(route) -> list[int]:
    return [
        s.employee_id
        for s in sorted(route.stops, key=lambda x: x.stop_order)
        if s.stop_type == "pickup" and s.employee_id is not None
    ]
