"""SQLAlchemy ORM models — import all tables for metadata registration."""

from app.models.base import Base
from app.models.dispatch import (
    DispatchAssignment,
    DispatchRouteStop,
    DispatchRun,
    DispatchRunEmployeeLocation,
    DispatchRunJob,
    DispatchVehicleRoute,
)
from app.models.employee import Employee, EmployeeLocation
from app.models.job import (
    Job,
    JobExcludedEmployee,
    JobIncludedEmployee,
    JobManualSubstitution,
    JobRequiredSkill,
)
from app.models.route_cache import RouteMatrixCache
from app.models.settings import AppSetting, BackupRecord, ExportRecord, OptimizationProfile
from app.models.skill import EmployeeSkill, Skill

__all__ = [
    "Base",
    "Employee",
    "EmployeeLocation",
    "Skill",
    "EmployeeSkill",
    "Job",
    "JobRequiredSkill",
    "JobManualSubstitution",
    "JobIncludedEmployee",
    "JobExcludedEmployee",
    "DispatchRun",
    "DispatchRunJob",
    "DispatchRunEmployeeLocation",
    "DispatchAssignment",
    "DispatchVehicleRoute",
    "DispatchRouteStop",
    "RouteMatrixCache",
    "OptimizationProfile",
    "ExportRecord",
    "AppSetting",
    "BackupRecord",
]
