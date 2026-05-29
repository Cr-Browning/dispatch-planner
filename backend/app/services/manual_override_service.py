"""Manual assignment and route overrides with recalculation."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    DispatchAssignment,
    DispatchRun,
    DispatchVehicleRoute,
)
from app.schemas.manual_override import (
    ManualOverrideRequest,
    ManualOverrideResponse,
    MoveAssignmentAction,
    MoveToVehicleAction,
    ReorderPickupsAction,
)
from app.services.eligibility_service import EligibilityService
from app.services.exceptions import NotFoundError, ValidationError
from app.services.route_planning_service import RoutePlanningService
from app.services.scarcity_service import ScarcityService


class ManualOverrideService:
    def __init__(self, db: Session, route_planner: RoutePlanningService) -> None:
        self._db = db
        self._route_planner = route_planner
        self._eligibility = EligibilityService(db)
        self._scarcity = ScarcityService(db)

    def apply_override(
        self, dispatch_run_id: int, request: ManualOverrideRequest
    ) -> ManualOverrideResponse:
        run = self._load_run(dispatch_run_id)
        if run.status not in ("reviewed", "draft"):
            raise ValidationError(
                f"Cannot override dispatch run in status '{run.status}'"
            )
        if not run.assignments:
            raise ValidationError("Dispatch run has no assignments to override")

        warnings: list[str] = []
        override_type: str

        if request.move_assignment is not None:
            override_type = "move_assignment"
            warnings.extend(
                self._move_assignment(run, request.move_assignment)
            )
            self._recalculate_routes(run)
        elif request.move_to_vehicle is not None:
            override_type = "move_to_vehicle"
            warnings.extend(
                self._move_to_vehicle(run, request.move_to_vehicle)
            )
        elif request.reorder_pickups is not None:
            override_type = "reorder_pickups"
            warnings.extend(
                self._reorder_pickups(run, request.reorder_pickups)
            )
        else:
            raise ValidationError("No override action provided")

        run.status = "reviewed"
        self._db.commit()
        run = self._load_run(dispatch_run_id)
        return self._build_response(run, warnings, override_type)

    def recalculate(self, dispatch_run_id: int) -> ManualOverrideResponse:
        run = self._load_run(dispatch_run_id)
        if not run.assignments:
            raise ValidationError("Dispatch run has no assignments to recalculate")
        jobs = [self._eligibility.load_job(link.job_id) for link in run.jobs]
        self._route_planner.recalculate_run(run, jobs)
        run.status = "reviewed"
        self._db.commit()
        run = self._load_run(dispatch_run_id)
        return self._build_response(run, [], "recalculate")

    def _move_assignment(
        self, run: DispatchRun, action: MoveAssignmentAction
    ) -> list[str]:
        warnings: list[str] = []
        assignment = self._get_assignment(run, action.employee_id)
        job_ids = {link.job_id for link in run.jobs}
        if action.to_job_id not in job_ids:
            raise ValidationError(f"Job {action.to_job_id} is not part of this dispatch run")

        jobs = [self._eligibility.load_job(jid) for jid in job_ids]
        employees = self._eligibility.load_employees([action.employee_id])
        employee = employees[0]
        target_job = next(j for j in jobs if j.id == action.to_job_id)

        assignment.job_id = action.to_job_id
        assignment.assigned_role = action.assigned_role
        assignment.manually_overridden = True

        scarcity_warning = self._scarcity.manual_override_scarcity_warning(
            employee, target_job, employees, jobs
        )
        if scarcity_warning:
            warnings.append(scarcity_warning)

        eligibility = self._eligibility.evaluate(employee, target_job)
        if not eligibility.eligible:
            warnings.append(
                f"Manual override: {employee.display_name or employee.id} may not be "
                f"eligible for {target_job.job_name or target_job.id}"
            )

        note = (
            f"Manually moved {employee.display_name or employee.id} to "
            f"{target_job.job_name or target_job.id}."
        )
        warnings.append(note)
        self._merge_assignment_warnings(assignment, warnings)
        return warnings

    def _move_to_vehicle(
        self, run: DispatchRun, action: MoveToVehicleAction
    ) -> list[str]:
        warnings: list[str] = []
        assignment = self._get_assignment(run, action.employee_id)
        target_route = self._get_vehicle_route(run, action.target_vehicle_route_id)

        if assignment.job_id != target_route.job_id:
            raise ValidationError(
                "Employee must be assigned to the same job as the target vehicle route"
            )

        source_route = self._find_passenger_route(run, action.employee_id)
        if source_route and source_route.id == target_route.id:
            return ["Employee is already on the target vehicle route."]

        target_passengers = self._passenger_ids(target_route)
        if action.employee_id not in target_passengers:
            target_passengers.append(action.employee_id)

        if len(target_passengers) + 1 > target_route.vehicle_capacity:
            warnings.append(
                f"Vehicle capacity exceeded ({len(target_passengers) + 1}/"
                f"{target_route.vehicle_capacity} occupants)."
            )

        if source_route and source_route.id != target_route.id:
            source_passengers = [
                pid for pid in self._passenger_ids(source_route) if pid != action.employee_id
            ]
            self._rebuild_route(run, source_route, source_passengers, "Manual vehicle move (source).")

        assignment.manually_overridden = True
        note = "Manually moved employee to another vehicle route."
        warnings.append(note)
        self._merge_assignment_warnings(assignment, [note])
        self._rebuild_route(
            run,
            target_route,
            target_passengers,
            "Manual vehicle move (target).",
        )
        return warnings

    def _reorder_pickups(
        self, run: DispatchRun, action: ReorderPickupsAction
    ) -> list[str]:
        warnings: list[str] = []
        route = self._get_vehicle_route(run, action.vehicle_route_id)
        current = self._passenger_ids(route)
        for emp_id in action.pickup_employee_ids:
            if emp_id not in current:
                raise ValidationError(
                    f"Employee {emp_id} is not a passenger on vehicle route {route.id}"
                )
        if set(action.pickup_employee_ids) != set(current):
            raise ValidationError("pickup_employee_ids must include all current passengers")

        for assignment in run.assignments:
            if assignment.employee_id in action.pickup_employee_ids:
                assignment.manually_overridden = True

        note = "Manually reordered pickup stops."
        warnings.append(note)
        self._rebuild_route(
            run,
            route,
            action.pickup_employee_ids,
            note,
            fixed_pickup_order=action.pickup_employee_ids,
        )
        return warnings

    def _rebuild_route(
        self,
        run: DispatchRun,
        route: DispatchVehicleRoute,
        passenger_ids: list[int],
        note: str,
        *,
        fixed_pickup_order: list[int] | None = None,
    ) -> None:
        job = self._eligibility.load_job(route.job_id)
        self._route_planner.rebuild_vehicle_route(
            route,
            run,
            job,
            passenger_ids=passenger_ids,
            fixed_pickup_order=fixed_pickup_order,
            manual_override_note=note,
        )

    def _recalculate_routes(self, run: DispatchRun) -> None:
        jobs = [self._eligibility.load_job(link.job_id) for link in run.jobs]
        self._route_planner.recalculate_run(run, jobs)

    def _load_run(self, dispatch_run_id: int) -> DispatchRun:
        run = self._db.scalars(
            select(DispatchRun)
            .where(DispatchRun.id == dispatch_run_id)
            .options(
                selectinload(DispatchRun.jobs),
                selectinload(DispatchRun.assignments),
                selectinload(DispatchRun.vehicle_routes).selectinload(
                    DispatchVehicleRoute.stops
                ),
            )
        ).first()
        if run is None:
            raise NotFoundError("DispatchRun", dispatch_run_id)
        return run

    def _get_assignment(
        self, run: DispatchRun, employee_id: int
    ) -> DispatchAssignment:
        assignment = next(
            (a for a in run.assignments if a.employee_id == employee_id), None
        )
        if assignment is None:
            raise NotFoundError("DispatchAssignment", employee_id)
        return assignment

    def _get_vehicle_route(
        self, run: DispatchRun, vehicle_route_id: int
    ) -> DispatchVehicleRoute:
        route = next(
            (r for r in run.vehicle_routes if r.id == vehicle_route_id), None
        )
        if route is None:
            raise NotFoundError("DispatchVehicleRoute", vehicle_route_id)
        return route

    def _find_passenger_route(
        self, run: DispatchRun, employee_id: int
    ) -> DispatchVehicleRoute | None:
        for route in run.vehicle_routes:
            if employee_id in self._passenger_ids(route):
                return route
        return None

    @staticmethod
    def _passenger_ids(route: DispatchVehicleRoute) -> list[int]:
        return [
            s.employee_id
            for s in sorted(route.stops, key=lambda x: x.stop_order)
            if s.stop_type == "pickup" and s.employee_id is not None
        ]

    @staticmethod
    def _merge_assignment_warnings(
        assignment: DispatchAssignment, new_warnings: list[str]
    ) -> None:
        existing: list[str] = []
        if assignment.warning_json:
            try:
                loaded = json.loads(assignment.warning_json)
                if isinstance(loaded, list):
                    existing = loaded
            except json.JSONDecodeError:
                existing = []
        merged = existing + [w for w in new_warnings if w not in existing]
        assignment.warning_json = json.dumps(merged) if merged else None

    def _build_response(
        self,
        run: DispatchRun,
        warnings: list[str],
        override_type: str,
    ) -> ManualOverrideResponse:
        from app.api.dispatch_mappers import route_to_response
        from app.schemas.dispatch import assignment_row_to_response

        assignment_warnings: list[str] = list(warnings)
        for row in run.assignments:
            if row.warning_json:
                try:
                    loaded = json.loads(row.warning_json)
                    if isinstance(loaded, list):
                        assignment_warnings.extend(loaded)
                except json.JSONDecodeError:
                    pass
        for route in run.vehicle_routes:
            if route.warning_json:
                try:
                    loaded = json.loads(route.warning_json)
                    if isinstance(loaded, list):
                        assignment_warnings.extend(loaded)
                except json.JSONDecodeError:
                    pass

        return ManualOverrideResponse(
            dispatch_run_id=run.id,
            status=run.status,
            assignments=[assignment_row_to_response(a) for a in run.assignments],
            vehicle_routes=[route_to_response(r) for r in run.vehicle_routes],
            warnings=sorted(set(assignment_warnings)),
            override_type=override_type,
        )
