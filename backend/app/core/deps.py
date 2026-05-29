"""FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.services.auth_service import AuthService
from app.services.employee_service import EmployeeService
from app.services.job_service import JobService
from app.services.location_service import LocationService
from app.routing import RoutingProvider, create_routing_provider
from app.services.dispatch_run_service import DispatchRunService
from app.services.dispatch_validation_service import DispatchValidationService
from app.services.eligibility_service import EligibilityService
from app.services.export_service import ExportService
from app.services.manual_override_service import ManualOverrideService
from app.services.optimization_service import OptimizationService
from app.services.route_planning_service import RoutePlanningService
from app.services.route_matrix_service import RouteMatrixService
from app.services.scarcity_service import ScarcityService
from app.services.settings_service import SettingsService
from app.services.skill_service import SkillService

security_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_auth_service(db: DbSession) -> AuthService:
    return AuthService(db)


def get_skill_service(db: DbSession) -> SkillService:
    return SkillService(db)


def get_employee_service(db: DbSession) -> EmployeeService:
    return EmployeeService(db)


def get_location_service(db: DbSession) -> LocationService:
    return LocationService(db)


def get_routing_provider() -> RoutingProvider:
    return create_routing_provider()


def get_job_service(
    db: DbSession,
    provider: Annotated[RoutingProvider, Depends(get_routing_provider)],
) -> JobService:
    return JobService(db, routing=provider)


def get_route_matrix_service(
    db: DbSession,
    provider: Annotated[RoutingProvider, Depends(get_routing_provider)],
) -> RouteMatrixService:
    return RouteMatrixService(db, provider)


def get_eligibility_service(db: DbSession) -> EligibilityService:
    return EligibilityService(db)


def get_scarcity_service(db: DbSession) -> ScarcityService:
    return ScarcityService(db)


def get_dispatch_run_service(db: DbSession) -> DispatchRunService:
    return DispatchRunService(db)


def get_dispatch_validation_service(db: DbSession) -> DispatchValidationService:
    return DispatchValidationService(db)


def get_route_planning_service(
    db: DbSession,
    matrix_service: Annotated[RouteMatrixService, Depends(get_route_matrix_service)],
) -> RoutePlanningService:
    return RoutePlanningService(db, matrix_service)


def get_optimization_service(
    db: DbSession,
    matrix_service: Annotated[RouteMatrixService, Depends(get_route_matrix_service)],
) -> OptimizationService:
    return OptimizationService(db, route_matrix_service=matrix_service)


def get_settings_service(db: DbSession) -> SettingsService:
    return SettingsService(db)


def get_export_service(db: DbSession) -> ExportService:
    return ExportService(db)


def get_manual_override_service(
    db: DbSession,
    route_planner: Annotated[RoutePlanningService, Depends(get_route_planning_service)],
) -> ManualOverrideService:
    return ManualOverrideService(db, route_planner)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username = decode_access_token(credentials.credentials)
    if username is None or not auth.validate_session_user(username):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username


CurrentUser = Annotated[str, Depends(get_current_user)]
