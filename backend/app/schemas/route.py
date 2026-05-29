"""Route solver input/output schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.models import Employee, Job
from app.routing.base import RouteMatrix, RoutingOptions
from app.schemas.assignment import ProposedAssignment


@dataclass(frozen=True)
class EmployeeRouteLocation:
    employee_id: int
    label: str
    address: str
    latitude: float
    longitude: float


@dataclass
class RouteStopProposal:
    stop_order: int
    stop_type: str
    employee_id: int | None = None
    job_id: int | None = None
    location_label: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    eta: datetime | None = None
    ride_time_minutes: float | None = None


@dataclass
class VehicleRouteProposal:
    job_id: int
    driver_employee_id: int
    vehicle_capacity: int
    passenger_ids: list[int] = field(default_factory=list)
    route_order: int = 1
    stops: list[RouteStopProposal] = field(default_factory=list)
    total_duration_minutes: float = 0.0
    total_distance_miles: float = 0.0
    arrival_time: datetime | None = None
    is_late: bool = False
    google_maps_url: str | None = None
    route_geometry_json: str | None = None
    reasoning: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass
class RouteSolution:
    routes: list[VehicleRouteProposal] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    reasoning_summary: str = ""


@dataclass
class RouteProblem:
    jobs: list[Job]
    assignments: list[ProposedAssignment]
    employees_by_id: dict[int, Employee]
    locations_by_employee: dict[int, EmployeeRouteLocation]
    matrix: RouteMatrix
    routing_options: RoutingOptions
    run_date: datetime | None = None
