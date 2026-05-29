"""Assignment solver input/output schemas."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models import Employee, Job
from app.schemas.eligibility import EligibilityResult, ScarceSkillInfo


@dataclass
class ProposedAssignment:
    employee_id: int
    job_id: int
    assigned_skill_id: int | None
    assigned_role: str
    substitution_used: bool = False
    substitution_reason: str | None = None
    reasoning: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass
class JobStaffingStatus:
    job_id: int
    required_headcount: int
    assigned_count: int
    required_slots_filled: int
    required_slots_total: int

    @property
    def is_fully_staffed(self) -> bool:
        return (
            self.assigned_count >= self.required_headcount
            and self.required_slots_filled >= self.required_slots_total
        )


@dataclass
class AssignmentSolution:
    assignments: list[ProposedAssignment]
    warnings: list[str] = field(default_factory=list)
    reasoning_summary: str = ""
    job_statuses: list[JobStaffingStatus] = field(default_factory=list)
    route_reasoning_summary: str = ""


@dataclass
class AssignmentProblem:
    employees: list[Employee]
    jobs: list[Job]
    eligibility: dict[tuple[int, int], EligibilityResult]
    scarce_skills: list[ScarceSkillInfo] = field(default_factory=list)
