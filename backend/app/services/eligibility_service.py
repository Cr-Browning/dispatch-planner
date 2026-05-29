"""Employee–job eligibility filtering and skill matching."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Employee,
    EmployeeSkill,
    Job,
    JobExcludedEmployee,
    JobIncludedEmployee,
    JobManualSubstitution,
    JobRequiredSkill,
)
from app.schemas.eligibility import EligibilityResult, SkillMatchInfo


class EligibilityService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def load_job(self, job_id: int) -> Job:
        job = self._db.scalars(
            select(Job)
            .where(Job.id == job_id)
            .options(
                selectinload(Job.required_skills).selectinload(JobRequiredSkill.skill),
                selectinload(Job.manual_substitutions).selectinload(
                    JobManualSubstitution.substitute_skill
                ),
                selectinload(Job.manual_substitutions).selectinload(
                    JobManualSubstitution.required_skill
                ),
                selectinload(Job.included_employees),
                selectinload(Job.excluded_employees),
            )
        ).first()
        if job is None:
            raise ValueError(f"Job {job_id} not found")
        return job

    def load_employees(self, employee_ids: list[int] | None = None) -> list[Employee]:
        stmt = select(Employee).options(
            selectinload(Employee.skills).selectinload(EmployeeSkill.skill)
        )
        if employee_ids is not None:
            stmt = stmt.where(Employee.id.in_(employee_ids))
        return list(self._db.scalars(stmt).unique().all())

    def evaluate(self, employee: Employee, job: Job) -> EligibilityResult:
        return evaluate_employee_for_job(employee, job)

    def build_matrix(
        self, employees: list[Employee], jobs: list[Job]
    ) -> dict[tuple[int, int], EligibilityResult]:
        return {
            (employee.id, job.id): self.evaluate(employee, job)
            for employee in employees
            for job in jobs
        }

    def eligible_pairs(
        self, employees: list[Employee], jobs: list[Job]
    ) -> list[EligibilityResult]:
        matrix = self.build_matrix(employees, jobs)
        return [r for r in matrix.values() if r.eligible]


def evaluate_employee_for_job(employee: Employee, job: Job) -> EligibilityResult:
    """Pure eligibility rules for one employee and one job."""
    result = EligibilityResult(employee_id=employee.id, job_id=job.id, eligible=False)

    excluded_ids = {row.employee_id for row in job.excluded_employees}
    included_ids = {row.employee_id for row in job.included_employees}
    result.is_must_include = employee.id in included_ids

    if not employee.active:
        result.reasons.append("Employee is inactive")
        if result.is_must_include:
            result.warnings.append("Must-include employee is inactive")
        return result

    if employee.id in excluded_ids:
        result.reasons.append("Employee is excluded from this job")
        return result

    skill_matches = _find_skill_matches(employee, job)
    result.skill_matches = skill_matches

    has_required_match = any(not m.is_preferred for m in skill_matches)
    has_preferred_match = any(m.is_preferred for m in skill_matches)

    if result.is_must_include:
        result.eligible = True
        if not has_required_match and not has_preferred_match:
            result.warnings.append(
                "Must-include employee does not match required or preferred skills"
            )
        return result

    if has_required_match or has_preferred_match:
        result.eligible = True
        return result

    if _allows_general_headcount_fill(job):
        if _has_general_labor(employee, job):
            result.eligible = True
            return result

    result.reasons.append("No matching required skill, substitution, or preferred skill")
    return result


def _find_skill_matches(employee: Employee, job: Job) -> list[SkillMatchInfo]:
    matches: list[SkillMatchInfo] = []
    employee_skills = {es.skill_id: es for es in employee.skills if es.skill}
    substitutions = _substitution_map(job)

    for req in job.required_skills:
        skill = req.skill
        if skill is None:
            continue
        direct = employee_skills.get(req.skill_id)
        if direct and direct.proficiency >= req.minimum_proficiency:
            matches.append(
                SkillMatchInfo(
                    skill_id=req.skill_id,
                    skill_name=skill.name,
                    required_skill_id=req.skill_id,
                    required_skill_name=skill.name,
                    match_type="direct",
                    proficiency=direct.proficiency,
                    is_preferred=req.is_preferred,
                )
            )
            continue

        sub_skill_id = substitutions.get(req.skill_id)
        if sub_skill_id is not None:
            sub_row = employee_skills.get(sub_skill_id)
            if sub_row and sub_row.proficiency >= req.minimum_proficiency:
                matches.append(
                    SkillMatchInfo(
                        skill_id=sub_skill_id,
                        skill_name=sub_row.skill.name if sub_row.skill else "",
                        required_skill_id=req.skill_id,
                        required_skill_name=skill.name,
                        match_type="substitution",
                        proficiency=sub_row.proficiency,
                        is_preferred=req.is_preferred,
                    )
                )

    return matches


def _substitution_map(job: Job) -> dict[int, int]:
    """Map required_skill_id -> substitute_skill_id when allowed."""
    mapping: dict[int, int] = {}
    for sub in job.manual_substitutions:
        if sub.allowed:
            mapping[sub.required_skill_id] = sub.substitute_skill_id
    return mapping


def _allows_general_headcount_fill(job: Job) -> bool:
    required_slots = sum(
        r.required_quantity for r in job.required_skills if not r.is_preferred
    )
    return job.required_headcount > required_slots


def _has_general_labor(employee: Employee, job: Job) -> bool:
    general_ids = {
        r.skill_id for r in job.required_skills if r.skill and r.skill.name == "General labor"
    }
    if not general_ids:
        return False
    for es in employee.skills:
        if es.skill_id in general_ids and es.proficiency >= 1:
            return True
    return any(
        es.skill and es.skill.name == "General labor" and es.proficiency >= 1
        for es in employee.skills
    )
