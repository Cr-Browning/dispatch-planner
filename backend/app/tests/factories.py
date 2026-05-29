"""Reusable test data builders for unit tests. Full catalog: app.seed.seed_data."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.models import (
    Employee,
    EmployeeLocation,
    EmployeeSkill,
    Job,
    JobIncludedEmployee,
    JobManualSubstitution,
    JobRequiredSkill,
    Skill,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def create_skill(session: Session, *, name: str = "Demo", active: bool = True) -> Skill:
    skill = Skill(name=name, active=active)
    session.add(skill)
    session.flush()
    return skill


def create_employee(
    session: Session,
    *,
    first_name: str = "Test",
    last_name: str = "User",
    active: bool = True,
    is_driver: bool = False,
    is_supervisor: bool = False,
    default_vehicle_capacity: int = 4,
) -> Employee:
    employee = Employee(
        first_name=first_name,
        last_name=last_name,
        active=active,
        is_driver=is_driver,
        is_supervisor=is_supervisor,
        default_vehicle_capacity=default_vehicle_capacity,
    )
    session.add(employee)
    session.flush()
    return employee


def create_location(
    session: Session,
    employee: Employee,
    *,
    label: str = "Home",
    address: str = "100 Main St",
    latitude: float = 40.0,
    longitude: float = -75.0,
    is_primary: bool = True,
) -> EmployeeLocation:
    location = EmployeeLocation(
        employee_id=employee.id,
        label=label,
        address=address,
        latitude=latitude,
        longitude=longitude,
        is_primary=is_primary,
    )
    session.add(location)
    session.flush()
    return location


def add_employee_skill(
    session: Session,
    employee: Employee,
    skill: Skill,
    proficiency: int,
) -> EmployeeSkill:
    row = EmployeeSkill(
        employee_id=employee.id,
        skill_id=skill.id,
        proficiency=proficiency,
    )
    session.add(row)
    session.flush()
    return row


def create_job(
    session: Session,
    *,
    job_name: str = "Test Job",
    address: str = "200 Job Rd",
    required_headcount: int = 2,
    arrival: datetime | None = None,
) -> Job:
    job = Job(
        job_name=job_name,
        address=address,
        required_arrival_time=arrival or datetime(2026, 6, 1, 8, 0, tzinfo=UTC),
        required_headcount=required_headcount,
    )
    session.add(job)
    session.flush()
    return job


def add_job_required_skill(
    session: Session,
    job: Job,
    skill: Skill,
    *,
    required_quantity: int = 1,
    minimum_proficiency: int = 1,
    is_preferred: bool = False,
) -> JobRequiredSkill:
    row = JobRequiredSkill(
        job_id=job.id,
        skill_id=skill.id,
        required_quantity=required_quantity,
        minimum_proficiency=minimum_proficiency,
        is_preferred=is_preferred,
    )
    session.add(row)
    session.flush()
    return row


def add_job_substitution(
    session: Session,
    job: Job,
    required_skill: Skill,
    substitute_skill: Skill,
) -> JobManualSubstitution:
    row = JobManualSubstitution(
        job_id=job.id,
        required_skill_id=required_skill.id,
        substitute_skill_id=substitute_skill.id,
        allowed=True,
    )
    session.add(row)
    session.flush()
    return row


def include_employee_on_job(session: Session, job: Job, employee: Employee) -> JobIncludedEmployee:
    row = JobIncludedEmployee(job_id=job.id, employee_id=employee.id)
    session.add(row)
    session.flush()
    return row
