"""Vehicle route solver — pickup order, capacity, ETAs (pure logic)."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.models import Employee, Job
from app.routing.base import RouteMatrix, RoutePoint, RoutingOptions
from app.routing.mock_provider import MockRoutingProvider
from app.schemas.assignment import ProposedAssignment
from app.schemas.route import (
    EmployeeRouteLocation,
    RouteProblem,
    RouteSolution,
    RouteStopProposal,
    VehicleRouteProposal,
)

ARRIVAL_BUFFER_MINUTES = 15
MAX_EXACT_PICKUP_PERMUTATIONS = 8
MAX_WORKER_RIDE_MINUTES = 75


@dataclass
class _DriverVehicle:
    employee: Employee
    capacity: int
    passenger_ids: list[int] = field(default_factory=list)

    @property
    def passenger_capacity(self) -> int:
        return max(0, self.capacity - 1)


class RouteSolver:
    """Build fewest-feasible-vehicle routes per job with optimized pickup order."""

    def solve(self, problem: RouteProblem) -> RouteSolution:
        warnings: list[str] = []
        reasoning_lines: list[str] = []
        routes: list[VehicleRouteProposal] = []
        route_order = 1

        assignments_by_job: dict[int, list[ProposedAssignment]] = {}
        for assignment in problem.assignments:
            assignments_by_job.setdefault(assignment.job_id, []).append(assignment)

        jobs_by_id = {j.id: j for j in problem.jobs}

        for job_id, job_assignments in assignments_by_job.items():
            job = jobs_by_id.get(job_id)
            if job is None:
                continue
            job_routes, job_warnings, job_reason = self._solve_job(
                job,
                job_assignments,
                problem,
                route_order,
            )
            routes.extend(job_routes)
            warnings.extend(job_warnings)
            if job_reason:
                reasoning_lines.append(job_reason)
            route_order += len(job_routes)

        summary = (
            "\n".join(reasoning_lines)
            if reasoning_lines
            else "No vehicle routes generated."
        )
        return RouteSolution(routes=routes, warnings=warnings, reasoning_summary=summary)

    def _solve_job(
        self,
        job: Job,
        assignments: list[ProposedAssignment],
        problem: RouteProblem,
        route_order_start: int,
    ) -> tuple[list[VehicleRouteProposal], list[str], str]:
        warnings: list[str] = []
        drivers = [
            problem.employees_by_id[a.employee_id]
            for a in assignments
            if a.assigned_role == "driver" and a.employee_id in problem.employees_by_id
        ]
        passengers = [
            a.employee_id
            for a in assignments
            if a.assigned_role != "driver"
        ]

        if not drivers:
            warnings.append(
                f"{job.job_name or f'Job {job.id}'}: no driver assigned; cannot build routes."
            )
            return [], warnings, ""

        vehicles = _pack_passengers_fewest_vehicles(drivers, passengers)
        if vehicles is None:
            warnings.append(
                f"{job.job_name or f'Job {job.id}'}: {len(passengers)} passengers exceed "
                f"combined vehicle capacity for assigned drivers."
            )
            vehicles = _pack_passengers_greedy_overflow(drivers, passengers, warnings)

        job_site = _job_route_point(job)
        required_arrival = job.required_arrival_time
        if required_arrival.tzinfo is None:
            required_arrival = required_arrival.replace(tzinfo=UTC)

        proposals: list[VehicleRouteProposal] = []
        for idx, vehicle in enumerate(vehicles):
            if not vehicle.passenger_ids and len(passengers) > 0 and idx == 0:
                continue
            driver_loc = problem.locations_by_employee.get(vehicle.employee.id)
            if driver_loc is None:
                warnings.append(
                    f"Driver {vehicle.employee.display_name or vehicle.employee.id} "
                    f"has no pickup location for {job.job_name}."
                )
                continue

            route = self._build_vehicle_route(
                job=job,
                driver=vehicle.employee,
                capacity=vehicle.capacity,
                passenger_ids=vehicle.passenger_ids,
                driver_location=driver_loc,
                job_site=job_site,
                matrix=problem.matrix,
                options=problem.routing_options,
                required_arrival=required_arrival,
                locations_by_employee=problem.locations_by_employee,
                route_order=route_order_start + idx,
                run_date=problem.run_date,
            )
            proposals.append(route)
            warnings.extend(route.warnings)

        vehicle_count = len(proposals)
        reason = (
            f"{job.job_name or f'Job {job.id}'}: {vehicle_count} vehicle(s) for "
            f"{len(passengers)} passenger(s) and {len(drivers)} driver(s)."
        )
        return proposals, warnings, reason

    def _build_vehicle_route(
        self,
        *,
        job: Job,
        driver: Employee,
        capacity: int,
        passenger_ids: list[int],
        driver_location: EmployeeRouteLocation,
        job_site: RoutePoint,
        matrix: RouteMatrix,
        options: RoutingOptions,
        required_arrival: datetime,
        locations_by_employee: dict[int, EmployeeRouteLocation],
        route_order: int,
        run_date: datetime | None = None,
        fixed_pickup_order: list[int] | None = None,
    ) -> VehicleRouteProposal:
        warnings: list[str] = []
        if len(passenger_ids) > capacity - 1:
            warnings.append(
                f"Vehicle for {driver.display_name or driver.id} exceeds capacity "
                f"({len(passenger_ids) + 1}/{capacity} occupants)."
            )

        pickup_id_order, duration, distance = self._resolve_pickup_order(
            passenger_ids=passenger_ids,
            driver_location=driver_location,
            job_site=job_site,
            locations_by_employee=locations_by_employee,
            matrix=matrix,
            options=options,
            warnings=warnings,
            fixed_pickup_order=fixed_pickup_order,
        )

        depart_at = _departure_time(run_date, required_arrival, duration)
        stops, arrival_time = _build_stops_with_etas(
            job=job,
            driver_id=driver.id,
            driver_location=driver_location,
            pickup_order=pickup_id_order,
            locations_by_employee=locations_by_employee,
            job_site=job_site,
            matrix=matrix,
            options=options,
            depart_at=depart_at,
        )

        deadline = required_arrival - timedelta(minutes=ARRIVAL_BUFFER_MINUTES)
        is_late = arrival_time > deadline
        if is_late:
            warnings.append(
                f"Route for {driver.display_name or driver.id} to "
                f"{job.job_name} arrives after the {ARRIVAL_BUFFER_MINUTES}-minute buffer."
            )

        ordered_route_points = [_location_route_point(driver_location)]
        for emp_id in pickup_id_order:
            loc = locations_by_employee[emp_id]
            ordered_route_points.append(_location_route_point(loc))
        ordered_route_points.append(job_site)

        route_result = MockRoutingProvider().compute_route(ordered_route_points, options)

        reasoning = (
            f"Driver {driver.display_name or driver.id}: "
            f"{len(pickup_id_order)} pickup(s), "
            f"{round(duration, 1)} min / {round(distance, 2)} mi, "
            f"{'late' if is_late else 'on time'}."
        )

        return VehicleRouteProposal(
            job_id=job.id,
            driver_employee_id=driver.id,
            vehicle_capacity=capacity,
            passenger_ids=pickup_id_order,
            route_order=route_order,
            stops=stops,
            total_duration_minutes=round(duration, 2),
            total_distance_miles=round(distance, 2),
            arrival_time=arrival_time,
            is_late=is_late,
            google_maps_url=route_result.google_maps_url,
            route_geometry_json=route_result.route_geometry_json,
            reasoning=reasoning,
            warnings=warnings,
        )

    def _resolve_pickup_order(
        self,
        *,
        passenger_ids: list[int],
        driver_location: EmployeeRouteLocation,
        job_site: RoutePoint,
        locations_by_employee: dict[int, EmployeeRouteLocation],
        matrix: RouteMatrix,
        options: RoutingOptions,
        warnings: list[str],
        fixed_pickup_order: list[int] | None = None,
    ) -> tuple[list[int], float, float]:
        pickup_points: list[tuple[int, RoutePoint]] = []
        for emp_id in passenger_ids:
            loc = locations_by_employee.get(emp_id)
            if loc is None:
                warnings.append(f"Passenger {emp_id} has no location; skipped from route.")
                continue
            pickup_points.append((emp_id, _location_route_point(loc)))

        if fixed_pickup_order is not None:
            pickup_id_order = [
                emp_id for emp_id in fixed_pickup_order if emp_id in {e for e, _ in pickup_points}
            ]
            ordered_points = []
            point_by_emp = {e: p for e, p in pickup_points}
            for emp_id in pickup_id_order:
                ordered_points.append(point_by_emp[emp_id])
            duration, distance = _leg_chain_duration(
                _location_route_point(driver_location),
                [*ordered_points, job_site],
                matrix,
            )
            return pickup_id_order, duration, distance

        ordered_pickups, duration, distance = _best_pickup_order(
            _location_route_point(driver_location),
            [p for _, p in pickup_points],
            job_site,
            matrix,
            options,
        )
        pickup_id_order = _match_pickup_order(pickup_points, ordered_pickups)
        return pickup_id_order, duration, distance

    def build_vehicle_route(
        self,
        *,
        job: Job,
        driver: Employee,
        capacity: int,
        passenger_ids: list[int],
        driver_location: EmployeeRouteLocation,
        locations_by_employee: dict[int, EmployeeRouteLocation],
        matrix: RouteMatrix,
        options: RoutingOptions,
        required_arrival: datetime,
        route_order: int = 1,
        run_date: datetime | None = None,
        fixed_pickup_order: list[int] | None = None,
        manual_override_note: str | None = None,
    ) -> VehicleRouteProposal:
        """Build or rebuild a single vehicle route (optionally with fixed pickup order)."""
        if required_arrival.tzinfo is None:
            required_arrival = required_arrival.replace(tzinfo=UTC)
        job_site = _job_route_point(job)
        route = self._build_vehicle_route(
            job=job,
            driver=driver,
            capacity=capacity,
            passenger_ids=passenger_ids,
            driver_location=driver_location,
            job_site=job_site,
            matrix=matrix,
            options=options,
            required_arrival=required_arrival,
            locations_by_employee=locations_by_employee,
            route_order=route_order,
            run_date=run_date,
            fixed_pickup_order=fixed_pickup_order,
        )
        if manual_override_note:
            route.reasoning = f"{route.reasoning} {manual_override_note}".strip()
            route.warnings.append(manual_override_note)
        ride_warnings = _long_ride_warnings(route.stops)
        route.warnings.extend(ride_warnings)
        return route


def _long_ride_warnings(stops: list[RouteStopProposal]) -> list[str]:
    warnings: list[str] = []
    for stop in stops:
        if stop.stop_type != "pickup":
            continue
        if stop.ride_time_minutes is not None and stop.ride_time_minutes > MAX_WORKER_RIDE_MINUTES:
            warnings.append(
                f"Pickup ride time {stop.ride_time_minutes:.0f} min exceeds "
                f"{MAX_WORKER_RIDE_MINUTES} min limit."
            )
    return warnings


def _pack_passengers_fewest_vehicles(
    drivers: list[Employee], passenger_ids: list[int]
) -> list[_DriverVehicle] | None:
    if not passenger_ids:
        return [_DriverVehicle(employee=drivers[0], capacity=drivers[0].default_vehicle_capacity)]

    sorted_drivers = sorted(
        drivers, key=lambda d: d.default_vehicle_capacity, reverse=True
    )
    for count in range(1, len(sorted_drivers) + 1):
        subset = sorted_drivers[:count]
        total_pax_cap = sum(max(0, d.default_vehicle_capacity - 1) for d in subset)
        if total_pax_cap >= len(passenger_ids):
            return _greedy_pack(subset, passenger_ids)
    return None


def _pack_passengers_greedy_overflow(
    drivers: list[Employee], passenger_ids: list[int], warnings: list[str]
) -> list[_DriverVehicle]:
    sorted_drivers = sorted(
        drivers, key=lambda d: d.default_vehicle_capacity, reverse=True
    )
    vehicles = [
        _DriverVehicle(employee=d, capacity=d.default_vehicle_capacity) for d in sorted_drivers
    ]
    remaining = list(passenger_ids)
    for vehicle in vehicles:
        while remaining and len(vehicle.passenger_ids) < vehicle.passenger_capacity:
            vehicle.passenger_ids.append(remaining.pop(0))
    if remaining:
        warnings.append(
            f"{len(remaining)} passenger(s) could not be assigned to a vehicle."
        )
    return [v for v in vehicles if v.passenger_ids or v is vehicles[0]]


def _greedy_pack(drivers: list[Employee], passenger_ids: list[int]) -> list[_DriverVehicle]:
    vehicles = [
        _DriverVehicle(employee=d, capacity=d.default_vehicle_capacity) for d in drivers
    ]
    remaining = list(passenger_ids)
    for vehicle in vehicles:
        while remaining and len(vehicle.passenger_ids) < vehicle.passenger_capacity:
            vehicle.passenger_ids.append(remaining.pop(0))
        if not remaining:
            break
    return [v for v in vehicles if v.passenger_ids]


def _best_pickup_order(
    start: RoutePoint,
    pickups: list[RoutePoint],
    end: RoutePoint,
    matrix: RouteMatrix,
    options: RoutingOptions,
) -> tuple[list[RoutePoint], float, float]:
    if not pickups:
        duration, distance = _leg_chain_duration(start, [end], matrix)
        return [], duration, distance

    points = [start, *pickups, end]

    best_order: list[RoutePoint] = pickups
    best_duration = float("inf")
    best_distance = float("inf")

    pickup_count = len(pickups)
    if pickup_count <= MAX_EXACT_PICKUP_PERMUTATIONS:
        permutations = itertools.permutations(pickups)
    else:
        permutations = [pickups]

    for perm in permutations:
        ordered = [start, *perm, end]
        duration, distance = _leg_chain_duration_from_indices(
            ordered, points, matrix
        )
        if duration < best_duration or (duration == best_duration and distance < best_distance):
            best_duration = duration
            best_distance = distance
            best_order = list(perm)

    return best_order, best_duration, best_distance


def _leg_chain_duration(
    start: RoutePoint, rest: list[RoutePoint], matrix: RouteMatrix
) -> tuple[float, float]:
    points = [start, *rest]
    return _leg_chain_duration_from_indices(points, points, matrix)


def _leg_chain_duration_from_indices(
    ordered: list[RoutePoint], matrix_points: list[RoutePoint], matrix: RouteMatrix
) -> tuple[float, float]:
    index_of = {id(p): i for i, p in enumerate(matrix_points)}
    total_minutes = 0.0
    total_miles = 0.0
    for i in range(len(ordered) - 1):
        oi = index_of[id(ordered[i])]
        di = index_of[id(ordered[i + 1])]
        cell = matrix.get(oi, di)
        if cell is None:
            from app.routing.mock_provider import leg_metrics

            minutes, miles = leg_metrics(ordered[i], ordered[i + 1], RoutingOptions())
            total_minutes += minutes
            total_miles += miles
        else:
            total_minutes += cell.duration_minutes
            total_miles += cell.distance_miles
    return total_minutes, total_miles


def _match_pickup_order(
    pickup_points: list[tuple[int, RoutePoint]], ordered_pickups: list[RoutePoint]
) -> list[int]:
    result: list[int] = []
    remaining = list(pickup_points)
    for target in ordered_pickups:
        for idx, (emp_id, point) in enumerate(remaining):
            if (
                point.latitude == target.latitude
                and point.longitude == target.longitude
            ):
                result.append(emp_id)
                remaining.pop(idx)
                break
    return result


def _build_stops_with_etas(
    *,
    job: Job,
    driver_id: int,
    driver_location: EmployeeRouteLocation,
    pickup_order: list[int],
    locations_by_employee: dict[int, EmployeeRouteLocation],
    job_site: RoutePoint,
    matrix: RouteMatrix,
    options: RoutingOptions,
    depart_at: datetime,
) -> tuple[list[RouteStopProposal], datetime]:
    stops: list[RouteStopProposal] = []
    current_time = depart_at
    chain: list[RoutePoint] = [_location_route_point(driver_location)]

    stops.append(
        RouteStopProposal(
            stop_order=1,
            stop_type="driver_start",
            employee_id=driver_id,
            location_label=driver_location.label,
            address=driver_location.address,
            latitude=driver_location.latitude,
            longitude=driver_location.longitude,
            eta=current_time,
            ride_time_minutes=0.0,
        )
    )

    order = 2
    for emp_id in pickup_order:
        loc = locations_by_employee[emp_id]
        dest = _location_route_point(loc)
        minutes, _ = _leg_between(chain[-1], dest, matrix, options)
        current_time += timedelta(minutes=minutes)
        stops.append(
            RouteStopProposal(
                stop_order=order,
                stop_type="pickup",
                employee_id=emp_id,
                location_label=loc.label,
                address=loc.address,
                latitude=loc.latitude,
                longitude=loc.longitude,
                eta=current_time,
                ride_time_minutes=round(minutes, 2),
            )
        )
        chain.append(dest)
        order += 1

    minutes, _ = _leg_between(chain[-1], job_site, matrix, options)
    current_time += timedelta(minutes=minutes)
    stops.append(
        RouteStopProposal(
            stop_order=order,
            stop_type="job_site",
            job_id=job.id,
            address=job.address,
            latitude=job.latitude,
            longitude=job.longitude,
            eta=current_time,
            ride_time_minutes=round(minutes, 2),
        )
    )
    return stops, current_time


def _leg_between(
    origin: RoutePoint,
    destination: RoutePoint,
    matrix: RouteMatrix,
    options: RoutingOptions,
) -> tuple[float, float]:
    from app.routing.mock_provider import leg_metrics

    if matrix.points:
        try:
            oi = next(
                i
                for i, p in enumerate(matrix.points)
                if p.latitude == origin.latitude and p.longitude == origin.longitude
            )
            di = next(
                i
                for i, p in enumerate(matrix.points)
                if p.latitude == destination.latitude and p.longitude == destination.longitude
            )
            cell = matrix.get(oi, di)
            if cell is not None:
                return cell.duration_minutes, cell.distance_miles
        except StopIteration:
            pass
    return leg_metrics(origin, destination, options)


def _location_route_point(loc: EmployeeRouteLocation) -> RoutePoint:
    return RoutePoint(
        latitude=loc.latitude,
        longitude=loc.longitude,
        label=loc.label,
        address=loc.address,
    )


def _departure_time(
    run_date: datetime | None,
    required_arrival: datetime,
    route_duration_minutes: float,
) -> datetime:
    """Depart at run-day 6:00 when known; otherwise back-schedule from arrival."""
    if run_date is not None:
        base = run_date
        if base.tzinfo is None:
            base = base.replace(tzinfo=UTC)
        return base.replace(hour=6, minute=0, second=0, microsecond=0)
    return required_arrival - timedelta(
        minutes=route_duration_minutes + ARRIVAL_BUFFER_MINUTES
    )


def _job_route_point(job: Job) -> RoutePoint:
    lat = job.latitude if job.latitude is not None else 0.0
    lng = job.longitude if job.longitude is not None else 0.0
    return RoutePoint(
        latitude=lat,
        longitude=lng,
        label=job.job_name,
        address=job.address,
    )


def build_route_matrix_points(
    problem: RouteProblem,
) -> list[RoutePoint]:
    """Collect unique route points for matrix computation."""
    seen: set[tuple[float, float]] = set()
    points: list[RoutePoint] = []

    def add(point: RoutePoint) -> None:
        key = (round(point.latitude, 5), round(point.longitude, 5))
        if key in seen:
            return
        seen.add(key)
        points.append(point)

    for loc in problem.locations_by_employee.values():
        add(_location_route_point(loc))
    for job in problem.jobs:
        add(_job_route_point(job))
    return points
