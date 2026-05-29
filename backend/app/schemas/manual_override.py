"""Manual override request schemas."""

from pydantic import BaseModel, Field, model_validator

from app.schemas.dispatch import AssignmentResponse, VehicleRouteResponse


class MoveAssignmentAction(BaseModel):
    employee_id: int
    to_job_id: int
    assigned_role: str = "worker"


class MoveToVehicleAction(BaseModel):
    employee_id: int
    target_vehicle_route_id: int


class ReorderPickupsAction(BaseModel):
    vehicle_route_id: int
    pickup_employee_ids: list[int] = Field(min_length=1)


class ManualOverrideRequest(BaseModel):
    move_assignment: MoveAssignmentAction | None = None
    move_to_vehicle: MoveToVehicleAction | None = None
    reorder_pickups: ReorderPickupsAction | None = None

    @model_validator(mode="after")
    def exactly_one_action(self):
        actions = [
            self.move_assignment is not None,
            self.move_to_vehicle is not None,
            self.reorder_pickups is not None,
        ]
        if sum(actions) != 1:
            raise ValueError("Exactly one override action must be provided")
        return self


class ManualOverrideResponse(BaseModel):
    dispatch_run_id: int
    status: str
    assignments: list[AssignmentResponse]
    vehicle_routes: list[VehicleRouteResponse] = []
    warnings: list[str]
    override_type: str
