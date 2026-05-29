"""Employee endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.errors import raise_http_for_domain
from app.api.mappers import employee_to_list_item, employee_to_response
from app.core.deps import CurrentUser, get_employee_service, get_location_service
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeListItem,
    EmployeeLocationCreate,
    EmployeeLocationResponse,
    EmployeeLocationUpdate,
    EmployeeResponse,
    EmployeeSkillCreate,
    EmployeeSkillResponse,
    EmployeeSkillUpdate,
    EmployeeUpdate,
)
from app.services.employee_service import EmployeeService
from app.services.location_service import LocationService

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeListItem])
def list_employees(
    _user: CurrentUser,
    service: Annotated[EmployeeService, Depends(get_employee_service)],
    active_only: bool = Query(default=False),
) -> list[EmployeeListItem]:
    return [employee_to_list_item(e) for e in service.list_employees(active_only=active_only)]


@router.post("", response_model=EmployeeResponse, status_code=201)
def create_employee(
    body: EmployeeCreate,
    _user: CurrentUser,
    service: Annotated[EmployeeService, Depends(get_employee_service)],
) -> EmployeeResponse:
    try:
        employee = service.create_employee(body)
    except Exception as exc:
        raise_http_for_domain(exc)
    return employee_to_response(employee)


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: int,
    _user: CurrentUser,
    service: Annotated[EmployeeService, Depends(get_employee_service)],
) -> EmployeeResponse:
    try:
        employee = service.get_employee(employee_id)
    except Exception as exc:
        raise_http_for_domain(exc)
    return employee_to_response(employee)


@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: int,
    body: EmployeeUpdate,
    _user: CurrentUser,
    service: Annotated[EmployeeService, Depends(get_employee_service)],
) -> EmployeeResponse:
    try:
        employee = service.update_employee(employee_id, body)
    except Exception as exc:
        raise_http_for_domain(exc)
    return employee_to_response(employee)


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    _user: CurrentUser,
    service: Annotated[EmployeeService, Depends(get_employee_service)],
) -> Response:
    try:
        service.delete_employee(employee_id)
    except Exception as exc:
        raise_http_for_domain(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{employee_id}/locations", response_model=EmployeeLocationResponse, status_code=201)
def create_location(
    employee_id: int,
    body: EmployeeLocationCreate,
    _user: CurrentUser,
    service: Annotated[LocationService, Depends(get_location_service)],
) -> EmployeeLocationResponse:
    try:
        location = service.create_location(employee_id, body)
    except Exception as exc:
        raise_http_for_domain(exc)
    return EmployeeLocationResponse.model_validate(location)


@router.put(
    "/{employee_id}/locations/{location_id}",
    response_model=EmployeeLocationResponse,
)
def update_location(
    employee_id: int,
    location_id: int,
    body: EmployeeLocationUpdate,
    _user: CurrentUser,
    service: Annotated[LocationService, Depends(get_location_service)],
) -> EmployeeLocationResponse:
    try:
        location = service.update_location(employee_id, location_id, body)
    except Exception as exc:
        raise_http_for_domain(exc)
    return EmployeeLocationResponse.model_validate(location)


@router.post("/{employee_id}/skills", response_model=EmployeeSkillResponse, status_code=201)
def add_employee_skill(
    employee_id: int,
    body: EmployeeSkillCreate,
    _user: CurrentUser,
    service: Annotated[EmployeeService, Depends(get_employee_service)],
) -> EmployeeSkillResponse:
    try:
        row = service.add_skill(employee_id, body)
    except Exception as exc:
        raise_http_for_domain(exc)
    return EmployeeService.skill_to_response(row)


@router.put("/{employee_id}/skills/{skill_id}", response_model=EmployeeSkillResponse)
def update_employee_skill(
    employee_id: int,
    skill_id: int,
    body: EmployeeSkillUpdate,
    _user: CurrentUser,
    service: Annotated[EmployeeService, Depends(get_employee_service)],
) -> EmployeeSkillResponse:
    try:
        row = service.update_skill(employee_id, skill_id, body)
    except Exception as exc:
        raise_http_for_domain(exc)
    return EmployeeService.skill_to_response(row)


@router.delete(
    "/{employee_id}/skills/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_employee_skill(
    employee_id: int,
    skill_id: int,
    _user: CurrentUser,
    service: Annotated[EmployeeService, Depends(get_employee_service)],
) -> Response:
    try:
        service.remove_skill(employee_id, skill_id)
    except Exception as exc:
        raise_http_for_domain(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{employee_id}/locations/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_location(
    employee_id: int,
    location_id: int,
    _user: CurrentUser,
    service: Annotated[LocationService, Depends(get_location_service)],
) -> Response:
    try:
        service.delete_location(employee_id, location_id)
    except Exception as exc:
        raise_http_for_domain(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
