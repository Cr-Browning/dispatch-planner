"""Job endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.errors import raise_http_for_domain
from app.api.mappers import (
    job_required_skill_to_response,
    job_substitution_to_response,
    job_to_list_item,
    job_to_response,
)
from app.core.deps import CurrentUser, get_job_service
from app.schemas.job import (
    JobCreate,
    JobDuplicateRequest,
    JobEmployeeLinkResponse,
    JobEmployeeRef,
    JobListItem,
    JobManualSubstitutionCreate,
    JobManualSubstitutionResponse,
    JobRequiredSkillCreate,
    JobRequiredSkillResponse,
    JobResponse,
    JobUpdate,
)
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobListItem])
def list_jobs(
    _user: CurrentUser,
    service: Annotated[JobService, Depends(get_job_service)],
) -> list[JobListItem]:
    return [job_to_list_item(j) for j in service.list_jobs()]


@router.post("", response_model=JobResponse, status_code=201)
def create_job(
    body: JobCreate,
    _user: CurrentUser,
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobResponse:
    try:
        job = service.create_job(body)
    except Exception as exc:
        raise_http_for_domain(exc)
    return job_to_response(job)


@router.post("/{job_id}/duplicate", response_model=JobResponse, status_code=201)
def duplicate_job(
    job_id: int,
    body: JobDuplicateRequest,
    _user: CurrentUser,
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobResponse:
    try:
        job = service.duplicate_job(
            job_id,
            run_date=body.run_date,
            job_name_suffix=body.job_name_suffix,
        )
    except Exception as exc:
        raise_http_for_domain(exc)
    return job_to_response(job)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    _user: CurrentUser,
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobResponse:
    try:
        job = service.get_job(job_id)
    except Exception as exc:
        raise_http_for_domain(exc)
    return job_to_response(job)


@router.put("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: int,
    body: JobUpdate,
    _user: CurrentUser,
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobResponse:
    try:
        job = service.update_job(job_id, body)
    except Exception as exc:
        raise_http_for_domain(exc)
    return job_to_response(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int,
    _user: CurrentUser,
    service: Annotated[JobService, Depends(get_job_service)],
) -> Response:
    try:
        service.delete_job(job_id)
    except Exception as exc:
        raise_http_for_domain(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{job_id}/required-skills", response_model=JobRequiredSkillResponse, status_code=201)
def add_required_skill(
    job_id: int,
    body: JobRequiredSkillCreate,
    _user: CurrentUser,
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobRequiredSkillResponse:
    try:
        row = service.add_required_skill(job_id, body)
    except Exception as exc:
        raise_http_for_domain(exc)
    return job_required_skill_to_response(row)


@router.delete(
    "/{job_id}/required-skills/{required_skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_required_skill(
    job_id: int,
    required_skill_id: int,
    _user: CurrentUser,
    service: Annotated[JobService, Depends(get_job_service)],
) -> Response:
    try:
        service.delete_required_skill(job_id, required_skill_id)
    except Exception as exc:
        raise_http_for_domain(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{job_id}/manual-substitutions",
    response_model=JobManualSubstitutionResponse,
    status_code=201,
)
def add_manual_substitution(
    job_id: int,
    body: JobManualSubstitutionCreate,
    _user: CurrentUser,
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobManualSubstitutionResponse:
    try:
        row = service.add_manual_substitution(job_id, body)
    except Exception as exc:
        raise_http_for_domain(exc)
    return job_substitution_to_response(row)


@router.post("/{job_id}/include-employee", response_model=JobEmployeeLinkResponse, status_code=201)
def include_employee(
    job_id: int,
    body: JobEmployeeRef,
    _user: CurrentUser,
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobEmployeeLinkResponse:
    try:
        row = service.include_employee(job_id, body)
    except Exception as exc:
        raise_http_for_domain(exc)
    return JobEmployeeLinkResponse.model_validate(row)


@router.post("/{job_id}/exclude-employee", response_model=JobEmployeeLinkResponse, status_code=201)
def exclude_employee(
    job_id: int,
    body: JobEmployeeRef,
    _user: CurrentUser,
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobEmployeeLinkResponse:
    try:
        row = service.exclude_employee(job_id, body)
    except Exception as exc:
        raise_http_for_domain(exc)
    return JobEmployeeLinkResponse.model_validate(row)
