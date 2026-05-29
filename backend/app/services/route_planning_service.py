"""Load locations, compute matrices, and persist vehicle routes."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    DispatchAssignment,
    DispatchRouteStop,
    DispatchRun,
    DispatchVehicleRoute,
    Employee,
    EmployeeLocation,
)
from app.routing.base import RoutingOptions
from app.schemas.assignment import AssignmentSolution, ProposedAssignment
from app.schemas.route import EmployeeRouteLocation, RouteProblem, VehicleRouteProposal
from app.services.route_matrix_service import RouteMatrixService
from app.services.route_solver import RouteSolver, build_route_matrix_points


class RoutePlanningService:
    def __init__(self, db: Session, matrix_service: RouteMatrixService) -> None:
        self._db = db
        self._matrix_service = matrix_service
        self._solver = RouteSolver()

    def plan_and_persist(
        self,
        dispatch_run: DispatchRun,
        solution: AssignmentSolution,
        jobs: list,
    ) -> str:
        if not solution.assignments:
            self._clear_routes(dispatch_run.id)
            return ""

        employee_ids = {a.employee_id for a in solution.assignments}
        employees = list(
            self._db.scalars(
                select(Employee)
                .where(Employee.id.in_(employee_ids))
                .options(selectinload(Employee.locations))
            ).all()
        )
        employees_by_id = {e.id: e for e in employees}
        locations = self._load_locations(employees)

        run_date = datetime.combine(
            dispatch_run.run_date, datetime.min.time(), tzinfo=UTC
        )
        options = RoutingOptions(
            tolls_allowed=True,
            departure_time=run_date,
        )

        problem = RouteProblem(
            jobs=jobs,
            assignments=solution.assignments,
            employees_by_id=employees_by_id,
            locations_by_employee=locations,
            matrix=self._matrix_service.get_matrix([], options),
            routing_options=options,
            run_date=run_date,
        )
        points = build_route_matrix_points(problem)
        matrix = self._matrix_service.get_matrix(points, options)
        problem.matrix = matrix

        route_solution = self._solver.solve(problem)
        self._clear_routes(dispatch_run.id)
        self._persist_routes(dispatch_run.id, route_solution.routes)

        solution.warnings.extend(route_solution.warnings)
        if route_solution.reasoning_summary:
            if solution.reasoning_summary:
                solution.reasoning_summary = (
                    f"{solution.reasoning_summary}\n\n{route_solution.reasoning_summary}"
                )
            else:
                solution.reasoning_summary = route_solution.reasoning_summary
        return route_solution.reasoning_summary

    def recalculate_run(self, dispatch_run: DispatchRun, jobs: list) -> str:
        """Rebuild all vehicle routes from persisted assignments."""
        assignments = list(
            self._db.scalars(
                select(DispatchAssignment).where(
                    DispatchAssignment.dispatch_run_id == dispatch_run.id
                )
            ).all()
        )
        proposed = [_assignment_to_proposed(a) for a in assignments]
        solution = AssignmentSolution(assignments=proposed)
        return self.plan_and_persist(dispatch_run, solution, jobs)

    def rebuild_vehicle_route(
        self,
        route: DispatchVehicleRoute,
        dispatch_run: DispatchRun,
        job,
        *,
        passenger_ids: list[int],
        fixed_pickup_order: list[int] | None = None,
        manual_override_note: str | None = None,
    ) -> VehicleRouteProposal:
        """Recompute and persist one vehicle route."""
        run_date = datetime.combine(
            dispatch_run.run_date, datetime.min.time(), tzinfo=UTC
        )
        options = RoutingOptions(tolls_allowed=True, departure_time=run_date)
        driver = self._db.get(Employee, route.driver_employee_id)
        if driver is None:
            raise ValueError(f"Driver {route.driver_employee_id} not found")

        employees = list(
            self._db.scalars(
                select(Employee)
                .where(Employee.id.in_([driver.id, *passenger_ids]))
                .options(selectinload(Employee.locations))
            ).all()
        )
        employees_by_id = {e.id: e for e in employees}
        locations = self._load_locations(employees)
        driver_loc = locations.get(driver.id)
        if driver_loc is None:
            raise ValueError(f"Driver {driver.id} has no primary location")

        problem = RouteProblem(
            jobs=[job],
            assignments=[],
            employees_by_id=employees_by_id,
            locations_by_employee=locations,
            matrix=self._matrix_service.get_matrix([], options),
            routing_options=options,
            run_date=run_date,
        )
        points = build_route_matrix_points(problem)
        matrix = self._matrix_service.get_matrix(points, options)

        required_arrival = job.required_arrival_time
        if required_arrival.tzinfo is None:
            required_arrival = required_arrival.replace(tzinfo=UTC)

        proposal = self._solver.build_vehicle_route(
            job=job,
            driver=driver,
            capacity=route.vehicle_capacity,
            passenger_ids=passenger_ids,
            driver_location=driver_loc,
            locations_by_employee=locations,
            matrix=matrix,
            options=options,
            required_arrival=required_arrival,
            route_order=route.route_order,
            run_date=run_date,
            fixed_pickup_order=fixed_pickup_order,
            manual_override_note=manual_override_note,
        )

        self._replace_route_row(route, proposal)
        return proposal

    def _replace_route_row(
        self, route: DispatchVehicleRoute, proposal: VehicleRouteProposal
    ) -> None:
        for stop in list(route.stops):
            self._db.delete(stop)
        route.total_duration_minutes = proposal.total_duration_minutes
        route.total_distance_miles = proposal.total_distance_miles
        route.arrival_time = proposal.arrival_time
        route.is_late = proposal.is_late
        route.google_maps_url = proposal.google_maps_url
        route.route_geometry_json = proposal.route_geometry_json
        route.reasoning = proposal.reasoning
        route.warning_json = json.dumps(proposal.warnings) if proposal.warnings else None
        self._db.flush()
        for stop in proposal.stops:
            self._db.add(
                DispatchRouteStop(
                    vehicle_route_id=route.id,
                    stop_order=stop.stop_order,
                    stop_type=stop.stop_type,
                    employee_id=stop.employee_id,
                    job_id=stop.job_id,
                    location_label=stop.location_label,
                    address=stop.address,
                    latitude=stop.latitude,
                    longitude=stop.longitude,
                    eta=stop.eta,
                    ride_time_minutes=stop.ride_time_minutes,
                )
            )

    def _load_locations(
        self, employees: list[Employee]
    ) -> dict[int, EmployeeRouteLocation]:
        locations: dict[int, EmployeeRouteLocation] = {}
        for employee in employees:
            loc = _primary_location(employee)
            if loc is None:
                continue
            lat, lng = loc.latitude, loc.longitude
            if lat is None or lng is None:
                continue
            locations[employee.id] = EmployeeRouteLocation(
                employee_id=employee.id,
                label=loc.label,
                address=loc.address,
                latitude=lat,
                longitude=lng,
            )
        return locations

    def _clear_routes(self, dispatch_run_id: int) -> None:
        routes = list(
            self._db.scalars(
                select(DispatchVehicleRoute).where(
                    DispatchVehicleRoute.dispatch_run_id == dispatch_run_id
                )
            ).all()
        )
        for route in routes:
            self._db.delete(route)

    def _persist_routes(
        self, dispatch_run_id: int, routes: list
    ) -> None:
        for proposal in routes:
            warning_json = json.dumps(proposal.warnings) if proposal.warnings else None
            row = DispatchVehicleRoute(
                dispatch_run_id=dispatch_run_id,
                job_id=proposal.job_id,
                driver_employee_id=proposal.driver_employee_id,
                vehicle_capacity=proposal.vehicle_capacity,
                route_order=proposal.route_order,
                total_duration_minutes=proposal.total_duration_minutes,
                total_distance_miles=proposal.total_distance_miles,
                arrival_time=proposal.arrival_time,
                is_late=proposal.is_late,
                google_maps_url=proposal.google_maps_url,
                route_geometry_json=proposal.route_geometry_json,
                reasoning=proposal.reasoning,
                warning_json=warning_json,
            )
            self._db.add(row)
            self._db.flush()

            for stop in proposal.stops:
                self._db.add(
                    DispatchRouteStop(
                        vehicle_route_id=row.id,
                        stop_order=stop.stop_order,
                        stop_type=stop.stop_type,
                        employee_id=stop.employee_id,
                        job_id=stop.job_id,
                        location_label=stop.location_label,
                        address=stop.address,
                        latitude=stop.latitude,
                        longitude=stop.longitude,
                        eta=stop.eta,
                        ride_time_minutes=stop.ride_time_minutes,
                    )
                )


def _assignment_to_proposed(row: DispatchAssignment) -> ProposedAssignment:
    warnings: list[str] = []
    if row.warning_json:
        try:
            warnings = json.loads(row.warning_json)
        except json.JSONDecodeError:
            warnings = []
    return ProposedAssignment(
        employee_id=row.employee_id,
        job_id=row.job_id,
        assigned_skill_id=row.assigned_skill_id,
        assigned_role=row.assigned_role or "worker",
        substitution_used=row.substitution_used,
        substitution_reason=row.substitution_reason,
        reasoning="",
        warnings=warnings if isinstance(warnings, list) else [],
    )


def _primary_location(employee: Employee) -> EmployeeLocation | None:
    if not employee.locations:
        return None
    primary = next((loc for loc in employee.locations if loc.is_primary), None)
    return primary or employee.locations[0]
