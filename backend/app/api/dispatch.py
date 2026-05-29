"""Dispatch run endpoints."""

from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import FileResponse

from app.api.errors import raise_http_for_domain
from app.core.deps import (
    CurrentUser,
    get_dispatch_run_service,
    get_dispatch_validation_service,
    get_export_service,
    get_manual_override_service,
    get_optimization_service,
)
from app.api.dispatch_mappers import route_to_response
from app.schemas.dispatch import (
    DispatchCopyTemplateResponse,
    DispatchRunCreate,
    DispatchRunResponse,
    DispatchValidationRequest,
    DispatchValidationResponse,
    SolveResponse,
    assignment_row_to_response,
    proposed_to_response,
)
from app.schemas.export import ExportCsvResponse
from app.schemas.manual_override import ManualOverrideRequest, ManualOverrideResponse
from app.services.dispatch_run_service import DispatchRunService
from app.services.dispatch_validation_service import DispatchValidationService
from app.services.export_service import ExportService
from app.services.manual_override_service import ManualOverrideService
from app.services.optimization_service import OptimizationService

router = APIRouter(prefix="/dispatch-runs", tags=["dispatch"])


@router.get("", response_model=list[DispatchRunResponse])
def list_dispatch_runs(
    _user: CurrentUser,
    service: Annotated[DispatchRunService, Depends(get_dispatch_run_service)],
) -> list[DispatchRunResponse]:
    return [_run_to_response(r) for r in service.list_runs()]


@router.get("/copy-template", response_model=DispatchCopyTemplateResponse)
def get_copy_template(
    _user: CurrentUser,
    service: Annotated[DispatchRunService, Depends(get_dispatch_run_service)],
    target_run_date: date | None = Query(default=None),
) -> DispatchCopyTemplateResponse:
    try:
        data = service.get_copy_template(target_run_date=target_run_date)
    except Exception as exc:
        raise_http_for_domain(exc)
    return DispatchCopyTemplateResponse(**data)


@router.post("/validate", response_model=DispatchValidationResponse)
def validate_dispatch_selection(
    body: DispatchValidationRequest,
    _user: CurrentUser,
    service: Annotated[DispatchValidationService, Depends(get_dispatch_validation_service)],
) -> DispatchValidationResponse:
    try:
        result = service.validate_selection(run_date=body.run_date, job_ids=body.job_ids)
    except Exception as exc:
        raise_http_for_domain(exc)
    return DispatchValidationResponse(**result)


@router.post("", response_model=DispatchRunResponse, status_code=status.HTTP_201_CREATED)
def create_dispatch_run(
    body: DispatchRunCreate,
    _user: CurrentUser,
    service: Annotated[DispatchRunService, Depends(get_dispatch_run_service)],
) -> DispatchRunResponse:
    run = service.create_run(
        run_date=body.run_date,
        name=body.name,
        job_ids=body.job_ids,
        optimization_profile_id=body.optimization_profile_id,
        employee_ids=body.employee_ids,
    )
    return _run_to_response(run)


@router.get("/{dispatch_run_id}/plan", response_model=SolveResponse)
def get_dispatch_plan(
    dispatch_run_id: int,
    _user: CurrentUser,
    service: Annotated[DispatchRunService, Depends(get_dispatch_run_service)],
) -> SolveResponse:
    try:
        run = service.get_run(dispatch_run_id)
    except Exception as exc:
        raise_http_for_domain(exc)
    assignments = [assignment_row_to_response(a) for a in run.assignments]
    vehicle_routes = [route_to_response(r) for r in run.vehicle_routes]
    warnings: list[str] = []
    for row in assignments:
        warnings.extend(row.warnings)
    for route in vehicle_routes:
        warnings.extend(route.warnings)
    return SolveResponse(
        dispatch_run_id=run.id,
        status=run.status,
        assignments=assignments,
        vehicle_routes=vehicle_routes,
        warnings=sorted(set(warnings)),
        reasoning_summary=run.reasoning_summary or "",
        route_reasoning_summary="",
    )


@router.get("/{dispatch_run_id}", response_model=DispatchRunResponse)
def get_dispatch_run(
    dispatch_run_id: int,
    _user: CurrentUser,
    service: Annotated[DispatchRunService, Depends(get_dispatch_run_service)],
) -> DispatchRunResponse:
    try:
        run = service.get_run(dispatch_run_id)
    except Exception as exc:
        raise_http_for_domain(exc)
    return _run_to_response(run)


@router.post("/{dispatch_run_id}/solve", response_model=SolveResponse)
def solve_dispatch_run(
    dispatch_run_id: int,
    _user: CurrentUser,
    optimization: Annotated[OptimizationService, Depends(get_optimization_service)],
    run_service: Annotated[DispatchRunService, Depends(get_dispatch_run_service)],
) -> SolveResponse:
    try:
        solution = optimization.solve_dispatch_run(dispatch_run_id)
        run = run_service.get_run(dispatch_run_id)
    except Exception as exc:
        raise_http_for_domain(exc)
    return SolveResponse(
        dispatch_run_id=dispatch_run_id,
        status=run.status,
        assignments=[proposed_to_response(a) for a in solution.assignments],
        vehicle_routes=[route_to_response(r) for r in run.vehicle_routes],
        warnings=solution.warnings,
        reasoning_summary=solution.reasoning_summary,
        route_reasoning_summary=solution.route_reasoning_summary,
    )


@router.post("/{dispatch_run_id}/export-csv", response_model=ExportCsvResponse)
def export_dispatch_run_csv(
    dispatch_run_id: int,
    _user: CurrentUser,
    export_service: Annotated[ExportService, Depends(get_export_service)],
) -> ExportCsvResponse:
    try:
        result = export_service.export_dispatch_run_csv(dispatch_run_id)
    except Exception as exc:
        raise_http_for_domain(exc)
    return ExportCsvResponse(
        dispatch_run_id=dispatch_run_id,
        export_record_id=result.export_record_id,
        file_path=result.file_path,
        row_count=result.row_count,
        created_at=result.created_at,
    )


@router.get("/{dispatch_run_id}/export-csv/download")
def download_dispatch_run_csv(
    dispatch_run_id: int,
    _user: CurrentUser,
    export_service: Annotated[ExportService, Depends(get_export_service)],
) -> FileResponse:
    try:
        result = export_service.export_dispatch_run_csv(dispatch_run_id)
    except Exception as exc:
        raise_http_for_domain(exc)
    path = Path(result.file_path)
    return FileResponse(
        path=path,
        filename=path.name,
        media_type="text/csv",
    )


@router.post("/{dispatch_run_id}/jobs/{job_id}/reassign", response_model=SolveResponse)
def reassign_dispatch_job(
    dispatch_run_id: int,
    job_id: int,
    _user: CurrentUser,
    optimization: Annotated[OptimizationService, Depends(get_optimization_service)],
    run_service: Annotated[DispatchRunService, Depends(get_dispatch_run_service)],
) -> SolveResponse:
    try:
        solution = optimization.reassign_job(dispatch_run_id, job_id)
        run = run_service.get_run(dispatch_run_id)
    except Exception as exc:
        raise_http_for_domain(exc)
    return SolveResponse(
        dispatch_run_id=dispatch_run_id,
        status=run.status,
        assignments=[proposed_to_response(a) for a in solution.assignments],
        vehicle_routes=[route_to_response(r) for r in run.vehicle_routes],
        warnings=solution.warnings,
        reasoning_summary=run.reasoning_summary or solution.reasoning_summary,
        route_reasoning_summary=solution.route_reasoning_summary,
    )


@router.post("/{dispatch_run_id}/recalculate", response_model=ManualOverrideResponse)
def recalculate_dispatch_run(
    dispatch_run_id: int,
    _user: CurrentUser,
    service: Annotated[ManualOverrideService, Depends(get_manual_override_service)],
) -> ManualOverrideResponse:
    try:
        return service.recalculate(dispatch_run_id)
    except Exception as exc:
        raise_http_for_domain(exc)


@router.post("/{dispatch_run_id}/manual-override", response_model=ManualOverrideResponse)
def manual_override(
    dispatch_run_id: int,
    body: ManualOverrideRequest,
    _user: CurrentUser,
    service: Annotated[ManualOverrideService, Depends(get_manual_override_service)],
) -> ManualOverrideResponse:
    try:
        return service.apply_override(dispatch_run_id, body)
    except Exception as exc:
        raise_http_for_domain(exc)


def _run_to_response(run) -> DispatchRunResponse:
    return DispatchRunResponse(
        id=run.id,
        run_date=run.run_date,
        name=run.name,
        optimization_profile_id=run.optimization_profile_id,
        status=run.status,
        reasoning_summary=run.reasoning_summary,
        created_at=run.created_at,
        updated_at=run.updated_at,
        job_ids=[link.job_id for link in run.jobs],
    )
