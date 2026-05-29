"""Vehicle route solver tests (Phase 10)."""

from datetime import UTC, datetime, timedelta

import pytest

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Employee, EmployeeLocation
from app.routing.base import RoutingOptions
from app.routing.mock_provider import MockRoutingProvider
from app.schemas.assignment import ProposedAssignment
from app.schemas.route import EmployeeRouteLocation, RouteProblem
from app.seed.seed_data import SEED_DRIVER_COUNT, SEED_EMPLOYEE_COUNT, SEED_JOB_COUNT
from app.services.eligibility_service import EligibilityService
from app.services.route_matrix_service import RouteMatrixService
from app.services.route_solver import RouteSolver, build_route_matrix_points


def _location_from_seed(
    employee_key: str, seed_catalog: dict, db_session
) -> EmployeeRouteLocation:
    emp_id = seed_catalog["employees"][employee_key].id
    loc = db_session.scalars(
        select(EmployeeLocation).where(
            EmployeeLocation.employee_id == emp_id,
            EmployeeLocation.is_primary.is_(True),
        )
    ).first()
    assert loc is not None
    assert loc.latitude is not None and loc.longitude is not None
    return EmployeeRouteLocation(
        employee_id=emp_id,
        label=loc.label,
        address=loc.address,
        latitude=loc.latitude,
        longitude=loc.longitude,
    )


def _route_problem(
    seed_catalog,
    db_session,
    *,
    job_key: str,
    assignments: list[ProposedAssignment],
    employee_keys: list[str],
) -> RouteProblem:
    eligibility = EligibilityService(db_session)
    job = eligibility.load_job(seed_catalog["jobs"][job_key].id)
    employee_ids = [seed_catalog["employees"][k].id for k in employee_keys]
    employees = list(
        db_session.scalars(
            select(Employee)
            .where(Employee.id.in_(employee_ids))
            .options(selectinload(Employee.locations))
        ).all()
    )
    employees_by_id = {e.id: e for e in employees}
    locations = {
        seed_catalog["employees"][k].id: _location_from_seed(k, seed_catalog, db_session)
        for k in employee_keys
    }
    options = RoutingOptions(tolls_allowed=True)
    problem = RouteProblem(
        jobs=[job],
        assignments=assignments,
        employees_by_id=employees_by_id,
        locations_by_employee=locations,
        matrix=RouteMatrixService(db_session, MockRoutingProvider()).get_matrix(
            [], options
        ),
        routing_options=options,
    )
    points = build_route_matrix_points(problem)
    problem.matrix = RouteMatrixService(
        db_session, MockRoutingProvider()
    ).get_matrix(points, options)
    return problem


@pytest.mark.phase10
def test_seed_catalog_has_expanded_roster(seed_catalog) -> None:
    assert len(seed_catalog["employees"]) == SEED_EMPLOYEE_COUNT
    assert SEED_EMPLOYEE_COUNT >= 10
    assert len(seed_catalog["jobs"]) == SEED_JOB_COUNT
    assert SEED_JOB_COUNT >= 4
    drivers = [e for e in seed_catalog["employees"].values() if e.is_driver]
    assert len(drivers) == SEED_DRIVER_COUNT
    assert SEED_DRIVER_COUNT >= 3


@pytest.mark.phase10
def test_vehicle_capacity_respected(seed_catalog, db_session) -> None:
    alex = seed_catalog["employees"]["alex_driver"]
    job = seed_catalog["jobs"]["demo_cleaning"]
    assignments = [
        ProposedAssignment(employee_id=alex.id, job_id=job.id, assigned_skill_id=None, assigned_role="driver"),
        ProposedAssignment(employee_id=seed_catalog["employees"]["jamie_drywall"].id, job_id=job.id, assigned_skill_id=None, assigned_role="worker"),
        ProposedAssignment(employee_id=seed_catalog["employees"]["chris_cleaner"].id, job_id=job.id, assigned_skill_id=None, assigned_role="worker"),
        ProposedAssignment(employee_id=seed_catalog["employees"]["casey_contents"].id, job_id=job.id, assigned_skill_id=None, assigned_role="worker"),
    ]
    problem = _route_problem(
        seed_catalog,
        db_session,
        job_key="demo_cleaning",
        assignments=assignments,
        employee_keys=["alex_driver", "jamie_drywall", "chris_cleaner", "casey_contents"],
    )
    solution = RouteSolver().solve(problem)
    route = solution.routes[0]
    assert len(route.passenger_ids) <= alex.default_vehicle_capacity - 1


@pytest.mark.phase10
def test_single_vehicle_for_small_crew(seed_catalog, db_session) -> None:
    alex = seed_catalog["employees"]["alex_driver"]
    job = seed_catalog["jobs"]["demo_cleaning"]
    assignments = [
        ProposedAssignment(employee_id=alex.id, job_id=job.id, assigned_skill_id=None, assigned_role="driver"),
        ProposedAssignment(employee_id=seed_catalog["employees"]["jamie_drywall"].id, job_id=job.id, assigned_skill_id=None, assigned_role="worker"),
        ProposedAssignment(employee_id=seed_catalog["employees"]["chris_cleaner"].id, job_id=job.id, assigned_skill_id=None, assigned_role="worker"),
    ]
    problem = _route_problem(
        seed_catalog,
        db_session,
        job_key="demo_cleaning",
        assignments=assignments,
        employee_keys=["alex_driver", "jamie_drywall", "chris_cleaner"],
    )
    solution = RouteSolver().solve(problem)
    assert len(solution.routes) == 1


@pytest.mark.phase10
def test_two_vehicles_when_capacity_exceeded(seed_catalog, db_session) -> None:
    alex = seed_catalog["employees"]["alex_driver"]
    morgan = seed_catalog["employees"]["morgan_lead"]
    job = seed_catalog["jobs"]["mitigation_large"]
    worker_keys = ["jamie_drywall", "chris_cleaner", "casey_contents", "pat_paint", "sam_framing"]
    assignments = [
        ProposedAssignment(employee_id=alex.id, job_id=job.id, assigned_skill_id=None, assigned_role="driver"),
        ProposedAssignment(employee_id=morgan.id, job_id=job.id, assigned_skill_id=None, assigned_role="driver"),
    ]
    for key in worker_keys:
        assignments.append(
            ProposedAssignment(
                employee_id=seed_catalog["employees"][key].id,
                job_id=job.id,
                assigned_skill_id=None,
                assigned_role="worker",
            )
        )
    problem = _route_problem(
        seed_catalog,
        db_session,
        job_key="mitigation_large",
        assignments=assignments,
        employee_keys=["alex_driver", "morgan_lead", *worker_keys],
    )
    solution = RouteSolver().solve(problem)
    assert len(solution.routes) >= 2
    total_passengers = sum(len(r.passenger_ids) for r in solution.routes)
    assert total_passengers == len(worker_keys)


@pytest.mark.phase10
def test_stops_order_driver_pickups_job(seed_catalog, db_session) -> None:
    alex = seed_catalog["employees"]["alex_driver"]
    job = seed_catalog["jobs"]["flooring_tile"]
    assignments = [
        ProposedAssignment(employee_id=alex.id, job_id=job.id, assigned_skill_id=None, assigned_role="driver"),
        ProposedAssignment(employee_id=seed_catalog["employees"]["taylor_tile"].id, job_id=job.id, assigned_skill_id=None, assigned_role="worker"),
    ]
    problem = _route_problem(
        seed_catalog,
        db_session,
        job_key="flooring_tile",
        assignments=assignments,
        employee_keys=["alex_driver", "taylor_tile"],
    )
    solution = RouteSolver().solve(problem)
    types = [s.stop_type for s in solution.routes[0].stops]
    assert types[0] == "driver_start"
    assert "pickup" in types
    assert types[-1] == "job_site"


@pytest.mark.phase10
def test_google_maps_url_generated(seed_catalog, db_session) -> None:
    morgan = seed_catalog["employees"]["morgan_lead"]
    job = seed_catalog["jobs"]["flooring_tile"]
    assignments = [
        ProposedAssignment(employee_id=morgan.id, job_id=job.id, assigned_skill_id=None, assigned_role="driver"),
        ProposedAssignment(employee_id=seed_catalog["employees"]["taylor_tile"].id, job_id=job.id, assigned_skill_id=None, assigned_role="worker"),
    ]
    problem = _route_problem(
        seed_catalog,
        db_session,
        job_key="flooring_tile",
        assignments=assignments,
        employee_keys=["morgan_lead", "taylor_tile"],
    )
    solution = RouteSolver().solve(problem)
    assert solution.routes[0].google_maps_url
    assert "google.com/maps" in solution.routes[0].google_maps_url


@pytest.mark.phase10
def test_late_arrival_warning(seed_catalog, db_session) -> None:
    eligibility = EligibilityService(db_session)
    job = eligibility.load_job(seed_catalog["jobs"]["demo_cleaning"].id)
    job.required_arrival_time = datetime(2026, 6, 15, 6, 1, tzinfo=UTC)
    alex = seed_catalog["employees"]["alex_driver"]
    assignments = [
        ProposedAssignment(employee_id=alex.id, job_id=job.id, assigned_skill_id=None, assigned_role="driver"),
        ProposedAssignment(employee_id=seed_catalog["employees"]["jamie_drywall"].id, job_id=job.id, assigned_skill_id=None, assigned_role="worker"),
        ProposedAssignment(employee_id=seed_catalog["employees"]["chris_cleaner"].id, job_id=job.id, assigned_skill_id=None, assigned_role="worker"),
        ProposedAssignment(employee_id=seed_catalog["employees"]["casey_contents"].id, job_id=job.id, assigned_skill_id=None, assigned_role="worker"),
    ]
    problem = _route_problem(
        seed_catalog,
        db_session,
        job_key="demo_cleaning",
        assignments=assignments,
        employee_keys=["alex_driver", "jamie_drywall", "chris_cleaner", "casey_contents"],
    )
    problem.jobs = [job]
    problem.run_date = datetime(2026, 6, 15, 0, 0, tzinfo=UTC)
    solution = RouteSolver().solve(problem)
    assert solution.routes[0].is_late
    assert any("buffer" in w.lower() for w in solution.routes[0].warnings)


@pytest.mark.phase10
def test_solve_via_api_includes_vehicle_routes(
    client, auth_headers, seed_catalog, db_session
) -> None:
    job_ids = [
        seed_catalog["jobs"]["demo_cleaning"].id,
        seed_catalog["jobs"]["flooring_tile"].id,
        seed_catalog["jobs"]["mitigation_large"].id,
    ]
    create = client.post(
        "/dispatch-runs",
        json={
            "run_date": "2026-06-15",
            "name": "Route Test Run",
            "job_ids": job_ids,
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    run_id = create.json()["id"]

    solve = client.post(f"/dispatch-runs/{run_id}/solve", headers=auth_headers)
    assert solve.status_code == 200
    body = solve.json()
    assert len(body["vehicle_routes"]) >= 2
    assert body["route_reasoning_summary"]
    first_route = body["vehicle_routes"][0]
    assert first_route["stops"]
    assert first_route["google_maps_url"]
