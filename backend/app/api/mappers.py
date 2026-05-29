"""ORM to response schema mappers."""

from app.models import Employee, Job, JobManualSubstitution, JobRequiredSkill
from app.schemas.employee import EmployeeListItem, EmployeeResponse, EmployeeSkillResponse
from app.schemas.job import (
    JobEmployeeLinkResponse,
    JobListItem,
    JobManualSubstitutionResponse,
    JobRequiredSkillResponse,
    JobResponse,
)
from app.services.employee_service import EmployeeService


def employee_to_response(employee: Employee) -> EmployeeResponse:
    return EmployeeResponse(
        id=employee.id,
        first_name=employee.first_name,
        last_name=employee.last_name,
        display_name=employee.display_name,
        active=employee.active,
        is_driver=employee.is_driver,
        is_supervisor=employee.is_supervisor,
        default_vehicle_capacity=employee.default_vehicle_capacity,
        notes=employee.notes,
        created_at=employee.created_at,
        updated_at=employee.updated_at,
        locations=employee.locations,
        skills=[EmployeeService.skill_to_response(s) for s in employee.skills],
    )


def employee_to_list_item(employee: Employee) -> EmployeeListItem:
    return EmployeeListItem.model_validate(employee)


def job_required_skill_to_response(row: JobRequiredSkill) -> JobRequiredSkillResponse:
    return JobRequiredSkillResponse(
        id=row.id,
        job_id=row.job_id,
        skill_id=row.skill_id,
        required_quantity=row.required_quantity,
        minimum_proficiency=row.minimum_proficiency,
        is_preferred=row.is_preferred,
        skill_name=row.skill.name if row.skill else None,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def job_substitution_to_response(row: JobManualSubstitution) -> JobManualSubstitutionResponse:
    return JobManualSubstitutionResponse(
        id=row.id,
        job_id=row.job_id,
        required_skill_id=row.required_skill_id,
        substitute_skill_id=row.substitute_skill_id,
        required_skill_name=row.required_skill.name if row.required_skill else None,
        substitute_skill_name=row.substitute_skill.name if row.substitute_skill else None,
        allowed=row.allowed,
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def job_to_response(job: Job) -> JobResponse:
    return JobResponse(
        id=job.id,
        job_name=job.job_name,
        client_name=job.client_name,
        address=job.address,
        latitude=job.latitude,
        longitude=job.longitude,
        required_arrival_time=job.required_arrival_time,
        required_headcount=job.required_headcount,
        tolls_allowed=job.tolls_allowed,
        return_trip_enabled=job.return_trip_enabled,
        dropoff_return_enabled=job.dropoff_return_enabled,
        notes=job.notes,
        created_at=job.created_at,
        updated_at=job.updated_at,
        required_skills=[job_required_skill_to_response(r) for r in job.required_skills],
        manual_substitutions=[job_substitution_to_response(s) for s in job.manual_substitutions],
        included_employees=[
            JobEmployeeLinkResponse.model_validate(e) for e in job.included_employees
        ],
        excluded_employees=[
            JobEmployeeLinkResponse.model_validate(e) for e in job.excluded_employees
        ],
    )


def _job_roles_summary(job: Job) -> str:
    if not job.required_skills:
        return "—"
    parts: list[str] = []
    for row in job.required_skills:
        name = row.skill.name if row.skill else "?"
        parts.append(f"{name}×{row.required_quantity}")
    return ", ".join(parts)


def job_to_list_item(job: Job) -> JobListItem:
    return JobListItem(
        id=job.id,
        job_name=job.job_name,
        client_name=job.client_name,
        address=job.address,
        required_arrival_time=job.required_arrival_time,
        required_headcount=job.required_headcount,
        roles_summary=_job_roles_summary(job),
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
