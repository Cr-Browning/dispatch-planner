"""Scarce-skill detection across same-day jobs."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.models import Employee, Job
from app.schemas.eligibility import EligibilityResult, ScarceSkillInfo
from app.services.eligibility_service import EligibilityService, evaluate_employee_for_job


class ScarcityService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._eligibility = EligibilityService(db)

    def detect_scarce_skills(
        self,
        employees: list[Employee],
        jobs: list[Job],
        *,
        eligibility_matrix: dict[tuple[int, int], EligibilityResult] | None = None,
    ) -> list[ScarceSkillInfo]:
        """Scarcity applies only when multiple jobs compete on the same day."""
        if len(jobs) < 2:
            return []

        matrix = eligibility_matrix or self._eligibility.build_matrix(employees, jobs)
        return compute_scarce_skills(employees, jobs, matrix)

    def scarcity_warning_for_assignment(
        self,
        employee_id: int,
        job_id: int,
        scarce_skills: list[ScarceSkillInfo],
        eligibility: EligibilityResult,
    ) -> str | None:
        """Warn when a scarce worker is assigned to a job that does not need their scarce skill."""
        if not scarce_skills:
            return None
        scarce_by_skill = {s.skill_id: s for s in scarce_skills}
        if not scarce_by_skill:
            return None

        if employee_id not in {eid for s in scarce_skills for eid in s.employee_ids}:
            return None

        required_skill_ids = {
            m.required_skill_id for m in eligibility.skill_matches if not m.is_preferred
        }
        for skill_id, info in scarce_by_skill.items():
            if employee_id not in info.employee_ids:
                continue
            if skill_id not in required_skill_ids:
                return (
                    f"Employee is scarce for {info.skill_name} but assigned to a job "
                    "that does not require that skill"
                )
        return None

    def manual_override_scarcity_warning(
        self,
        employee: Employee,
        job: Job,
        employees: list[Employee],
        jobs: list[Job],
    ) -> str | None:
        """Warn when manual override assigns a scarce worker to a lower-priority job."""
        scarce = self.detect_scarce_skills(employees, jobs)
        eligibility = evaluate_employee_for_job(employee, job)
        return self.scarcity_warning_for_assignment(
            employee.id, job.id, scarce, eligibility
        )


def compute_scarce_skills(
    employees: list[Employee],
    jobs: list[Job],
    eligibility_matrix: dict[tuple[int, int], EligibilityResult],
) -> list[ScarceSkillInfo]:
    """Count supply vs demand for each required (non-preferred) skill."""
    if len(jobs) < 2:
        return []

    demand: dict[int, tuple[str, int]] = {}
    for job in jobs:
        for req in job.required_skills:
            if req.is_preferred or req.skill is None:
                continue
            skill_id = req.skill_id
            name = req.skill.name
            prev = demand.get(skill_id, (name, 0))
            demand[skill_id] = (name, prev[1] + req.required_quantity)

    supply: dict[int, set[int]] = defaultdict(set)
    for employee in employees:
        for job in jobs:
            result = eligibility_matrix.get((employee.id, job.id))
            if result is None or not result.eligible:
                continue
            for match in result.skill_matches:
                if match.is_preferred:
                    continue
                if match.match_type == "direct":
                    supply[match.required_skill_id].add(employee.id)
                elif match.match_type == "substitution":
                    supply[match.required_skill_id].add(employee.id)

    scarce: list[ScarceSkillInfo] = []
    for skill_id, (name, demanded) in demand.items():
        employee_ids = sorted(supply.get(skill_id, set()))
        available = len(employee_ids)
        info = ScarceSkillInfo(
            skill_id=skill_id,
            skill_name=name,
            available_count=available,
            demanded_count=demanded,
            employee_ids=employee_ids,
        )
        if info.is_scarce or (available > 0 and available <= demanded):
            scarce.append(info)
    return scarce
