"""Job template and related CRUD."""

from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Job,
    JobExcludedEmployee,
    JobIncludedEmployee,
    JobManualSubstitution,
    JobRequiredSkill,
    Skill,
)
from app.schemas.job import (
    JobCreate,
    JobEmployeeRef,
    JobManualSubstitutionCreate,
    JobRequiredSkillCreate,
    JobUpdate,
)
from app.routing.base import RoutingProvider
from app.routing.errors import GeocodeNotFoundError
from app.services.employee_service import EmployeeService
from app.services.exceptions import ConflictError, NotFoundError, ValidationError
from app.services.skill_service import SkillService


class JobService:
    def __init__(self, db: Session, routing: RoutingProvider | None = None) -> None:
        self._db = db
        self._routing = routing
        self._skills = SkillService(db)
        self._employees = EmployeeService(db)

    def _base_query(self):
        return select(Job).options(
            selectinload(Job.required_skills).selectinload(JobRequiredSkill.skill),
            selectinload(Job.manual_substitutions).selectinload(
                JobManualSubstitution.required_skill
            ),
            selectinload(Job.manual_substitutions).selectinload(
                JobManualSubstitution.substitute_skill
            ),
            selectinload(Job.included_employees),
            selectinload(Job.excluded_employees),
        )

    def list_jobs(self) -> list[Job]:
        return list(
            self._db.scalars(self._base_query().order_by(Job.required_arrival_time)).unique().all()
        )

    def get_job(self, job_id: int) -> Job:
        job = self._db.scalars(self._base_query().where(Job.id == job_id)).first()
        if job is None:
            raise NotFoundError("Job", job_id)
        return job

    def create_job(self, data: JobCreate) -> Job:
        job = Job(
            job_name=data.job_name,
            client_name=data.client_name,
            address=data.address.strip(),
            latitude=data.latitude,
            longitude=data.longitude,
            required_arrival_time=data.required_arrival_time,
            required_headcount=data.required_headcount,
            tolls_allowed=data.tolls_allowed,
            return_trip_enabled=data.return_trip_enabled,
            dropoff_return_enabled=data.dropoff_return_enabled,
            notes=data.notes,
        )
        self._db.add(job)
        self._db.flush()
        self._maybe_geocode(job)
        self._db.commit()
        return self.get_job(job.id)

    def update_job(self, job_id: int, data: JobUpdate) -> Job:
        job = self.get_job(job_id)
        updates = data.model_dump(exclude_unset=True)
        if "address" in updates and updates["address"] is not None:
            updates["address"] = updates["address"].strip()
        address_changed = "address" in updates
        coords_in_payload = "latitude" in updates or "longitude" in updates
        for key, value in updates.items():
            setattr(job, key, value)
        if address_changed and not coords_in_payload:
            job.latitude = None
            job.longitude = None
            self._maybe_geocode(job)
        elif job.latitude is None and job.longitude is None:
            self._maybe_geocode(job)
        self._db.commit()
        return self.get_job(job_id)

    def _maybe_geocode(self, job: Job) -> None:
        if self._routing is None:
            return
        if job.latitude is not None and job.longitude is not None:
            return
        address = job.address.strip()
        if not address:
            return
        try:
            result = self._routing.geocode(address)
        except GeocodeNotFoundError as exc:
            raise ValidationError(f"Could not geocode address: {address}") from exc
        job.latitude = result.latitude
        job.longitude = result.longitude

    def delete_job(self, job_id: int) -> None:
        job = self.get_job(job_id)
        self._db.delete(job)
        self._db.commit()

    def duplicate_job(
        self,
        job_id: int,
        *,
        run_date: date | None = None,
        job_name_suffix: str = " (copy)",
    ) -> Job:
        source = self.get_job(job_id)
        arrival = source.required_arrival_time
        if run_date is not None:
            if isinstance(arrival, datetime):
                arrival = datetime.combine(run_date, arrival.time(), tzinfo=arrival.tzinfo)
            else:
                arrival = datetime.combine(run_date, time(8, 0))

        job_name = source.job_name
        if job_name:
            job_name = f"{job_name}{job_name_suffix}"

        job = Job(
            job_name=job_name,
            client_name=source.client_name,
            address=source.address,
            latitude=source.latitude,
            longitude=source.longitude,
            required_arrival_time=arrival,
            required_headcount=source.required_headcount,
            tolls_allowed=source.tolls_allowed,
            return_trip_enabled=source.return_trip_enabled,
            dropoff_return_enabled=source.dropoff_return_enabled,
            notes=source.notes,
        )
        self._db.add(job)
        self._db.flush()

        for row in source.required_skills:
            self._db.add(
                JobRequiredSkill(
                    job_id=job.id,
                    skill_id=row.skill_id,
                    required_quantity=row.required_quantity,
                    minimum_proficiency=row.minimum_proficiency,
                    is_preferred=row.is_preferred,
                )
            )
        for row in source.manual_substitutions:
            self._db.add(
                JobManualSubstitution(
                    job_id=job.id,
                    required_skill_id=row.required_skill_id,
                    substitute_skill_id=row.substitute_skill_id,
                    allowed=row.allowed,
                    notes=row.notes,
                )
            )
        for row in source.included_employees:
            self._db.add(
                JobIncludedEmployee(job_id=job.id, employee_id=row.employee_id)
            )
        for row in source.excluded_employees:
            self._db.add(
                JobExcludedEmployee(job_id=job.id, employee_id=row.employee_id)
            )

        self._maybe_geocode(job)
        self._db.commit()
        return self.get_job(job.id)

    def add_required_skill(self, job_id: int, data: JobRequiredSkillCreate) -> JobRequiredSkill:
        self.get_job(job_id)
        self._skills.get_skill(data.skill_id)
        row = JobRequiredSkill(
            job_id=job_id,
            skill_id=data.skill_id,
            required_quantity=data.required_quantity,
            minimum_proficiency=data.minimum_proficiency,
            is_preferred=data.is_preferred,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        row.skill = self._db.get(Skill, data.skill_id)
        return row

    def delete_required_skill(self, job_id: int, required_skill_id: int) -> None:
        self.get_job(job_id)
        row = self._db.get(JobRequiredSkill, required_skill_id)
        if row is None or row.job_id != job_id:
            raise NotFoundError("JobRequiredSkill", required_skill_id)
        self._db.delete(row)
        self._db.commit()

    def add_manual_substitution(
        self, job_id: int, data: JobManualSubstitutionCreate
    ) -> JobManualSubstitution:
        self.get_job(job_id)
        self._skills.get_skill(data.required_skill_id)
        self._skills.get_skill(data.substitute_skill_id)
        row = JobManualSubstitution(
            job_id=job_id,
            required_skill_id=data.required_skill_id,
            substitute_skill_id=data.substitute_skill_id,
            allowed=data.allowed,
            notes=data.notes,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        row.required_skill = self._skills.get_skill(row.required_skill_id)
        row.substitute_skill = self._skills.get_skill(row.substitute_skill_id)
        return row

    def include_employee(self, job_id: int, data: JobEmployeeRef) -> JobIncludedEmployee:
        self.get_job(job_id)
        self._employees.get_employee(data.employee_id)
        existing = self._db.scalars(
            select(JobIncludedEmployee).where(
                JobIncludedEmployee.job_id == job_id,
                JobIncludedEmployee.employee_id == data.employee_id,
            )
        ).first()
        if existing is not None:
            return existing
        row = JobIncludedEmployee(job_id=job_id, employee_id=data.employee_id)
        self._db.add(row)
        try:
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            raise ConflictError("Could not include employee on job") from exc
        self._db.refresh(row)
        return row

    def exclude_employee(self, job_id: int, data: JobEmployeeRef) -> JobExcludedEmployee:
        self.get_job(job_id)
        self._employees.get_employee(data.employee_id)
        existing = self._db.scalars(
            select(JobExcludedEmployee).where(
                JobExcludedEmployee.job_id == job_id,
                JobExcludedEmployee.employee_id == data.employee_id,
            )
        ).first()
        if existing is not None:
            return existing
        row = JobExcludedEmployee(job_id=job_id, employee_id=data.employee_id)
        self._db.add(row)
        try:
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            raise ConflictError("Could not exclude employee from job") from exc
        self._db.refresh(row)
        return row
