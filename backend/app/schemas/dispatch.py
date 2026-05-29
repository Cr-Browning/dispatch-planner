"""Dispatch run API schemas."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.assignment import ProposedAssignment


class DispatchValidationRequest(BaseModel):
    run_date: date
    job_ids: list[int] = Field(default_factory=list)


class DispatchValidationIssue(BaseModel):
    level: str
    message: str


class DispatchValidationResponse(BaseModel):
    ready: bool
    issues: list[DispatchValidationIssue] = []


class DispatchRunCreate(BaseModel):
    run_date: date
    name: str = Field(min_length=1, max_length=200)
    job_ids: list[int] = Field(min_length=1)
    optimization_profile_id: int | None = None
    employee_ids: list[int] | None = None


class DispatchCopyTemplateResponse(BaseModel):
    source_run_id: int
    source_run_name: str
    source_run_date: date
    job_ids: list[int]
    job_ids_on_run_date: list[int] = []
    job_ids_off_run_date: list[int] = []
    jobs_on_run_date_count: int = 0
    suggested_run_date: date
    suggested_name: str


class DispatchRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_date: date
    name: str
    optimization_profile_id: int | None
    status: str
    reasoning_summary: str | None
    created_at: datetime
    updated_at: datetime
    job_ids: list[int] = []


class AssignmentResponse(BaseModel):
    employee_id: int
    job_id: int
    assigned_skill_id: int | None
    assigned_role: str | None
    substitution_used: bool
    substitution_reason: str | None
    manually_overridden: bool = False
    reasoning: str = ""
    warnings: list[str] = []


class RouteStopResponse(BaseModel):
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


class VehicleRouteResponse(BaseModel):
    id: int
    job_id: int
    driver_employee_id: int
    vehicle_capacity: int
    passenger_ids: list[int]
    route_order: int
    total_duration_minutes: float | None
    total_distance_miles: float | None
    arrival_time: datetime | None
    is_late: bool
    google_maps_url: str | None
    route_geometry_json: str | None = None
    reasoning: str | None
    warnings: list[str] = []
    stops: list[RouteStopResponse] = []


class SolveResponse(BaseModel):
    dispatch_run_id: int
    status: str
    assignments: list[AssignmentResponse]
    vehicle_routes: list[VehicleRouteResponse] = []
    warnings: list[str]
    reasoning_summary: str
    route_reasoning_summary: str = ""


def proposed_to_response(p: ProposedAssignment) -> AssignmentResponse:
    return AssignmentResponse(
        employee_id=p.employee_id,
        job_id=p.job_id,
        assigned_skill_id=p.assigned_skill_id,
        assigned_role=p.assigned_role,
        substitution_used=p.substitution_used,
        substitution_reason=p.substitution_reason,
        reasoning=p.reasoning,
        warnings=p.warnings,
        manually_overridden=False,
    )


def assignment_row_to_response(row) -> AssignmentResponse:
    import json

    warnings: list[str] = []
    if row.warning_json:
        try:
            loaded = json.loads(row.warning_json)
            if isinstance(loaded, list):
                warnings = loaded
        except json.JSONDecodeError:
            warnings = []
    return AssignmentResponse(
        employee_id=row.employee_id,
        job_id=row.job_id,
        assigned_skill_id=row.assigned_skill_id,
        assigned_role=row.assigned_role,
        substitution_used=row.substitution_used,
        substitution_reason=row.substitution_reason,
        manually_overridden=row.manually_overridden,
        reasoning="",
        warnings=warnings,
    )
