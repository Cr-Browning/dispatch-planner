"""Orchestrates eligibility, scarcity, and assignment solving for dispatch runs."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import DispatchAssignment, DispatchRun, DispatchRunJob, DispatchVehicleRoute
from app.schemas.assignment import AssignmentProblem, AssignmentSolution, ProposedAssignment
from app.services.assignment_solver import AssignmentSolver
from app.services.eligibility_service import EligibilityService
from app.services.exceptions import NotFoundError, ValidationError
from app.services.route_planning_service import RoutePlanningService
from app.services.route_matrix_service import RouteMatrixService
from app.services.scarcity_service import ScarcityService


class OptimizationService:
    def __init__(
        self,
        db: Session,
        route_matrix_service: RouteMatrixService | None = None,
    ) -> None:
        self._db = db
        self._eligibility = EligibilityService(db)
        self._scarcity = ScarcityService(db)
        self._solver = AssignmentSolver()
        self._route_planner = (
            RoutePlanningService(db, route_matrix_service)
            if route_matrix_service is not None
            else None
        )

    def load_dispatch_run(self, dispatch_run_id: int) -> DispatchRun:
        run = self._db.scalars(
            select(DispatchRun)
            .where(DispatchRun.id == dispatch_run_id)
            .options(selectinload(DispatchRun.jobs).selectinload(DispatchRunJob.job))
        ).first()
        if run is None:
            raise NotFoundError("DispatchRun", dispatch_run_id)
        return run

    def solve_dispatch_run(self, dispatch_run_id: int) -> AssignmentSolution:
        run = self.load_dispatch_run(dispatch_run_id)
        run.status = "solving"
        self._db.flush()

        jobs = [self._eligibility.load_job(link.job_id) for link in run.jobs]
        employee_ids = self._employee_ids_for_run(run)
        employees = self._eligibility.load_employees(employee_ids)

        matrix = self._eligibility.build_matrix(employees, jobs)
        scarce = self._scarcity.detect_scarce_skills(employees, jobs, eligibility_matrix=matrix)

        problem = AssignmentProblem(
            employees=employees,
            jobs=jobs,
            eligibility=matrix,
            scarce_skills=scarce,
        )
        solution = self._solver.solve(problem)

        self._clear_assignments(run.id)
        self._persist_assignments(run.id, solution)

        if self._route_planner is not None and solution.assignments:
            solution.route_reasoning_summary = self._route_planner.plan_and_persist(
                run, solution, jobs
            )

        run.reasoning_summary = solution.reasoning_summary
        run.status = "reviewed" if solution.assignments else "failed"
        self._db.commit()
        return solution

    def reassign_job(self, dispatch_run_id: int, job_id: int) -> AssignmentSolution:
        """Re-run assignment for one job while keeping other jobs' crews fixed."""
        run = self.load_dispatch_run(dispatch_run_id)
        run_job_ids = {link.job_id for link in run.jobs}
        if job_id not in run_job_ids:
            raise ValidationError(f"Job {job_id} is not part of dispatch run {dispatch_run_id}")

        if self._route_planner is None:
            raise ValidationError("Route planning is not configured")

        all_assignments = list(
            self._db.scalars(
                select(DispatchAssignment).where(
                    DispatchAssignment.dispatch_run_id == dispatch_run_id
                )
            ).all()
        )
        locked_employee_ids = {
            row.employee_id for row in all_assignments if row.job_id != job_id
        }

        for row in list(all_assignments):
            if row.job_id == job_id:
                self._db.delete(row)

        for route in list(
            self._db.scalars(
                select(DispatchVehicleRoute).where(
                    DispatchVehicleRoute.dispatch_run_id == dispatch_run_id,
                    DispatchVehicleRoute.job_id == job_id,
                )
            ).all()
        ):
            self._db.delete(route)
        self._db.flush()

        job = self._eligibility.load_job(job_id)
        employee_ids = self._employee_ids_for_run(run)
        employees = self._eligibility.load_employees(employee_ids)
        available = [e for e in employees if e.id not in locked_employee_ids]
        if not available:
            raise ValidationError("No available employees to assign to this job")

        matrix = self._eligibility.build_matrix(available, [job])
        scarce = self._scarcity.detect_scarce_skills(
            available, [job], eligibility_matrix=matrix
        )
        problem = AssignmentProblem(
            employees=available,
            jobs=[job],
            eligibility=matrix,
            scarce_skills=scarce,
        )
        partial = self._solver.solve(problem)
        self._persist_assignments(dispatch_run_id, partial)

        merged_assignments = list(
            self._db.scalars(
                select(DispatchAssignment).where(
                    DispatchAssignment.dispatch_run_id == dispatch_run_id
                )
            ).all()
        )
        proposed: list[ProposedAssignment] = []
        for row in merged_assignments:
            warnings: list[str] = []
            if row.warning_json:
                try:
                    loaded = json.loads(row.warning_json)
                    if isinstance(loaded, list):
                        warnings = loaded
                except json.JSONDecodeError:
                    warnings = []
            proposed.append(
                ProposedAssignment(
                    employee_id=row.employee_id,
                    job_id=row.job_id,
                    assigned_skill_id=row.assigned_skill_id,
                    assigned_role=row.assigned_role or "worker",
                    substitution_used=row.substitution_used,
                    substitution_reason=row.substitution_reason,
                    reasoning="",
                    warnings=warnings,
                )
            )
        solution = AssignmentSolution(
            assignments=proposed,
            warnings=partial.warnings,
            reasoning_summary=partial.reasoning_summary,
        )
        all_jobs = [self._eligibility.load_job(link.job_id) for link in run.jobs]
        solution.route_reasoning_summary = self._route_planner.plan_and_persist(
            run, solution, all_jobs
        )
        run.reasoning_summary = (
            f"{run.reasoning_summary or ''}\n\nReassigned job {job_id}: "
            f"{partial.reasoning_summary}"
        ).strip()
        run.status = "reviewed"
        self._db.commit()
        return solution

    def _employee_ids_for_run(self, run: DispatchRun) -> list[int] | None:
        if not run.settings_json:
            return None
        try:
            settings = json.loads(run.settings_json)
        except json.JSONDecodeError:
            return None
        ids = settings.get("employee_ids")
        if isinstance(ids, list) and ids:
            return [int(i) for i in ids]
        return None

    def _clear_assignments(self, dispatch_run_id: int) -> None:
        rows = list(
            self._db.scalars(
                select(DispatchAssignment).where(
                    DispatchAssignment.dispatch_run_id == dispatch_run_id
                )
            ).all()
        )
        for row in rows:
            self._db.delete(row)

    def _persist_assignments(self, dispatch_run_id: int, solution: AssignmentSolution) -> None:
        for proposed in solution.assignments:
            warning_json = json.dumps(proposed.warnings) if proposed.warnings else None
            self._db.add(
                DispatchAssignment(
                    dispatch_run_id=dispatch_run_id,
                    job_id=proposed.job_id,
                    employee_id=proposed.employee_id,
                    assigned_skill_id=proposed.assigned_skill_id,
                    assigned_role=proposed.assigned_role,
                    substitution_used=proposed.substitution_used,
                    substitution_reason=proposed.substitution_reason,
                    warning_json=warning_json,
                    manually_overridden=False,
                )
            )
