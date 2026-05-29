"""Multi-job employee-to-job assignment solver (pure logic, no database)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from app.models import Employee, Job
from app.schemas.assignment import (
    AssignmentProblem,
    AssignmentSolution,
    JobStaffingStatus,
    ProposedAssignment,
)
from app.schemas.eligibility import EligibilityResult, ScarceSkillInfo, SkillMatchInfo


@dataclass
class _SkillSlot:
    job_id: int
    required_skill_id: int
    skill_name: str
    is_preferred: bool
    filled: bool = False


@dataclass
class _SolverState:
    assigned_employee_to_job: dict[int, int] = field(default_factory=dict)
    assignments: list[ProposedAssignment] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    reasoning_lines: list[str] = field(default_factory=list)
    slots: list[_SkillSlot] = field(default_factory=list)
    job_assignments: dict[int, list[int]] = field(default_factory=lambda: defaultdict(list))


class AssignmentSolver:
    """Assign employees to jobs for one dispatch day."""

    def solve(self, problem: AssignmentProblem) -> AssignmentSolution:
        state = _SolverState()
        employees_by_id = {e.id: e for e in problem.employees}
        jobs_by_id = {j.id: j for j in problem.jobs}

        state.slots = _build_skill_slots(problem.jobs)

        self._assign_must_includes(problem, state, employees_by_id, jobs_by_id)
        self._assign_scarce_workers(problem, state, employees_by_id, jobs_by_id)
        self._fill_required_slots(problem, state, employees_by_id, jobs_by_id)
        self._fill_headcount(problem, state, employees_by_id, jobs_by_id)

        job_statuses = _build_job_statuses(problem.jobs, state)
        for status in job_statuses:
            if not status.is_fully_staffed:
                job = jobs_by_id[status.job_id]
                name = job.job_name or f"Job {job.id}"
                state.warnings.append(
                    f"{name} is understaffed: {status.assigned_count}/"
                    f"{status.required_headcount} workers, "
                    f"{status.required_slots_filled}/{status.required_slots_total} required skill slots"
                )

        summary = "\n".join(state.reasoning_lines) if state.reasoning_lines else "No assignments made."
        return AssignmentSolution(
            assignments=state.assignments,
            warnings=state.warnings,
            reasoning_summary=summary,
            job_statuses=job_statuses,
        )

    def _assign_must_includes(
        self,
        problem: AssignmentProblem,
        state: _SolverState,
        employees_by_id: dict[int, Employee],
        jobs_by_id: dict[int, Job],
    ) -> None:
        for job in problem.jobs:
            for link in job.included_employees:
                emp_id = link.employee_id
                if emp_id in state.assigned_employee_to_job:
                    state.warnings.append(
                        f"Must-include employee {emp_id} already assigned elsewhere"
                    )
                    continue
                employee = employees_by_id.get(emp_id)
                if employee is None:
                    continue
                result = problem.eligibility.get((emp_id, job.id))
                if result is None:
                    continue
                self._commit_assignment(
                    problem, state, employee, job, result, reason_prefix="Must-include: "
                )

    def _assign_scarce_workers(
        self,
        problem: AssignmentProblem,
        state: _SolverState,
        employees_by_id: dict[int, Employee],
        jobs_by_id: dict[int, Job],
    ) -> None:
        if len(problem.jobs) < 2:
            return

        for scarce in problem.scarce_skills:
            for slot in state.slots:
                if slot.filled or slot.is_preferred:
                    continue
                if slot.required_skill_id != scarce.skill_id:
                    continue
                for emp_id in scarce.employee_ids:
                    if emp_id in state.assigned_employee_to_job:
                        continue
                    result = problem.eligibility.get((emp_id, slot.job_id))
                    if result is None or not result.eligible:
                        continue
                    match = _best_match_for_slot(result, slot.required_skill_id)
                    if match is None:
                        continue
                    employee = employees_by_id[emp_id]
                    job = jobs_by_id[slot.job_id]
                    self._commit_assignment(
                        problem,
                        state,
                        employee,
                        job,
                        result,
                        match=match,
                        reason_prefix=(
                            f"Preserved scarce {scarce.skill_name} skill for "
                            f"{job.job_name or job.id}: "
                        ),
                    )
                    slot.filled = True
                    break

    def _fill_required_slots(
        self,
        problem: AssignmentProblem,
        state: _SolverState,
        employees_by_id: dict[int, Employee],
        jobs_by_id: dict[int, Job],
    ) -> None:
        required_slots = [s for s in state.slots if not s.is_preferred and not s.filled]
        for slot in required_slots:
            candidates = self._rank_candidates_for_slot(problem, state, slot)
            if not candidates:
                continue
            emp_id, match = candidates[0]
            employee = employees_by_id[emp_id]
            job = jobs_by_id[slot.job_id]
            result = problem.eligibility[(emp_id, slot.job_id)]
            self._commit_assignment(
                problem,
                state,
                employee,
                job,
                result,
                match=match,
                reason_prefix=f"Filled {slot.skill_name} requirement: ",
            )
            slot.filled = True

    def _fill_headcount(
        self,
        problem: AssignmentProblem,
        state: _SolverState,
        employees_by_id: dict[int, Employee],
        jobs_by_id: dict[int, Job],
    ) -> None:
        for job in problem.jobs:
            while len(state.job_assignments[job.id]) < job.required_headcount:
                candidates = self._rank_headcount_candidates(problem, state, job)
                if not candidates:
                    break
                emp_id = candidates[0]
                employee = employees_by_id[emp_id]
                result = problem.eligibility[(emp_id, job.id)]
                match = _pick_headcount_match(result)
                self._commit_assignment(
                    problem,
                    state,
                    employee,
                    job,
                    result,
                    match=match,
                    reason_prefix="Headcount fill: ",
                )

    def _rank_candidates_for_slot(
        self,
        problem: AssignmentProblem,
        state: _SolverState,
        slot: _SkillSlot,
    ) -> list[tuple[int, SkillMatchInfo]]:
        ranked: list[tuple[int, SkillMatchInfo, int, int]] = []
        for employee in problem.employees:
            if employee.id in state.assigned_employee_to_job:
                continue
            if not self._allow_scarce_assignment(problem, state, employee.id, slot.job_id):
                continue
            result = problem.eligibility.get((employee.id, slot.job_id))
            if result is None or not result.eligible:
                continue
            match = _best_match_for_slot(result, slot.required_skill_id)
            if match is None:
                continue
            type_score = 0 if match.match_type == "direct" else 1
            ranked.append((employee.id, match, type_score, -match.proficiency))
        ranked.sort(key=lambda x: (x[2], x[3]))
        return [(e, m) for e, m, _, _ in ranked]

    def _rank_headcount_candidates(
        self,
        problem: AssignmentProblem,
        state: _SolverState,
        job: Job,
    ) -> list[int]:
        ranked: list[tuple[int, int, int]] = []
        for employee in problem.employees:
            if employee.id in state.assigned_employee_to_job:
                continue
            if not self._allow_scarce_assignment(problem, state, employee.id, job.id):
                continue
            result = problem.eligibility.get((employee.id, job.id))
            if result is None or not result.eligible:
                continue
            match = _pick_headcount_match(result)
            type_score = 0 if match and match.match_type == "direct" else 1
            prof = -(match.proficiency if match else 0)
            ranked.append((employee.id, type_score, prof))
        ranked.sort(key=lambda x: (x[1], x[2]))
        return [e for e, _, _ in ranked]

    def _allow_scarce_assignment(
        self,
        problem: AssignmentProblem,
        state: _SolverState,
        employee_id: int,
        job_id: int,
    ) -> bool:
        scarce_skills_for_emp = [
            s
            for s in problem.scarce_skills
            if employee_id in s.employee_ids and (s.is_scarce or s.available_count <= s.demanded_count)
        ]
        if not scarce_skills_for_emp:
            return True
        for info in scarce_skills_for_emp:
            if _job_still_needs_skill(state, problem.jobs, info.skill_id, exclude_job_id=job_id):
                if not _job_needs_skill(job_id, info.skill_id, state.slots):
                    return False
        return True

    def _commit_assignment(
        self,
        problem: AssignmentProblem,
        state: _SolverState,
        employee: Employee,
        job: Job,
        result: EligibilityResult,
        *,
        match: SkillMatchInfo | None = None,
        reason_prefix: str = "",
    ) -> None:
        if employee.id in state.assigned_employee_to_job:
            return
        chosen = match or _pick_headcount_match(result)
        role = _employee_role(employee)
        substitution_used = bool(chosen and chosen.match_type == "substitution")
        sub_reason = None
        if substitution_used and chosen:
            sub_reason = (
                f"{chosen.skill_name} substituted for {chosen.required_skill_name}"
            )

        job_name = job.job_name or f"Job {job.id}"
        emp_name = employee.display_name or f"{employee.first_name} {employee.last_name}"
        skill_note = ""
        if chosen:
            skill_note = f" using {chosen.skill_name} ({chosen.match_type})"
        reason = f"{reason_prefix}Assigned {emp_name} to {job_name}{skill_note}."

        warnings: list[str] = list(result.warnings)
        for scarce in problem.scarce_skills:
            w = _scarcity_misuse_warning(employee.id, job, scarce, chosen)
            if w:
                warnings.append(w)

        state.assignments.append(
            ProposedAssignment(
                employee_id=employee.id,
                job_id=job.id,
                assigned_skill_id=chosen.skill_id if chosen else None,
                assigned_role=role,
                substitution_used=substitution_used,
                substitution_reason=sub_reason,
                reasoning=reason,
                warnings=warnings,
            )
        )
        state.assigned_employee_to_job[employee.id] = job.id
        state.job_assignments[job.id].append(employee.id)
        state.reasoning_lines.append(reason)


def _build_skill_slots(jobs: list[Job]) -> list[_SkillSlot]:
    slots: list[_SkillSlot] = []
    for job in jobs:
        for req in job.required_skills:
            if req.skill is None:
                continue
            for _ in range(req.required_quantity):
                slots.append(
                    _SkillSlot(
                        job_id=job.id,
                        required_skill_id=req.skill_id,
                        skill_name=req.skill.name,
                        is_preferred=req.is_preferred,
                    )
                )
    return slots


def _build_job_statuses(jobs: list[Job], state: _SolverState) -> list[JobStaffingStatus]:
    statuses: list[JobStaffingStatus] = []
    for job in jobs:
        required_total = sum(
            r.required_quantity for r in job.required_skills if not r.is_preferred
        )
        filled = sum(
            1
            for s in state.slots
            if s.job_id == job.id and not s.is_preferred and s.filled
        )
        statuses.append(
            JobStaffingStatus(
                job_id=job.id,
                required_headcount=job.required_headcount,
                assigned_count=len(state.job_assignments[job.id]),
                required_slots_filled=filled,
                required_slots_total=required_total,
            )
        )
    return statuses


def _best_match_for_slot(
    result: EligibilityResult, required_skill_id: int
) -> SkillMatchInfo | None:
    direct = [m for m in result.skill_matches if m.required_skill_id == required_skill_id]
    if not direct:
        return None
    direct.sort(key=lambda m: (0 if m.match_type == "direct" else 1, -m.proficiency))
    return direct[0]


def _pick_headcount_match(result: EligibilityResult) -> SkillMatchInfo | None:
    if not result.skill_matches:
        return None
    preferred = [m for m in result.skill_matches if m.is_preferred]
    pool = preferred if preferred else result.skill_matches
    pool = sorted(pool, key=lambda m: (0 if m.match_type == "direct" else 1, -m.proficiency))
    return pool[0]


def _employee_role(employee: Employee) -> str:
    if employee.is_driver:
        return "driver"
    if employee.is_supervisor:
        return "supervisor"
    return "worker"


def _job_needs_skill(job_id: int, skill_id: int, slots: list[_SkillSlot]) -> bool:
    return any(
        s.job_id == job_id and s.required_skill_id == skill_id and not s.is_preferred
        for s in slots
    )


def _job_still_needs_skill(
    state: _SolverState, jobs: list[Job], skill_id: int, exclude_job_id: int
) -> bool:
    for slot in state.slots:
        if slot.job_id == exclude_job_id:
            continue
        if slot.required_skill_id == skill_id and not slot.is_preferred and not slot.filled:
            return True
    return False


def _scarcity_misuse_warning(
    employee_id: int,
    job: Job,
    scarce: ScarceSkillInfo,
    match: SkillMatchInfo | None,
) -> str | None:
    if employee_id not in scarce.employee_ids:
        return None
    if match and match.required_skill_id == scarce.skill_id and not match.is_preferred:
        return None
    job_needs = any(
        r.skill_id == scarce.skill_id and not r.is_preferred for r in job.required_skills
    )
    if job_needs:
        return None
    return (
        f"Scarce {scarce.skill_name} worker assigned to job that does not require that skill"
    )
