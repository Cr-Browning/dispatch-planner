"""Dispatch run, assignment, and route models."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee, EmployeeLocation
    from app.models.job import Job
    from app.models.settings import ExportRecord, OptimizationProfile
    from app.models.skill import Skill


class DispatchRun(Base, TimestampMixin):
    __tablename__ = "dispatch_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    optimization_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("optimization_profiles.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False, index=True)
    settings_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    reasoning_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    optimization_profile: Mapped[OptimizationProfile | None] = relationship(
        back_populates="dispatch_runs"
    )
    jobs: Mapped[list[DispatchRunJob]] = relationship(
        back_populates="dispatch_run", cascade="all, delete-orphan"
    )
    employee_locations: Mapped[list[DispatchRunEmployeeLocation]] = relationship(
        back_populates="dispatch_run", cascade="all, delete-orphan"
    )
    assignments: Mapped[list[DispatchAssignment]] = relationship(
        back_populates="dispatch_run", cascade="all, delete-orphan"
    )
    vehicle_routes: Mapped[list[DispatchVehicleRoute]] = relationship(
        back_populates="dispatch_run", cascade="all, delete-orphan"
    )
    export_records: Mapped[list[ExportRecord]] = relationship(back_populates="dispatch_run")


class DispatchRunJob(Base):
    __tablename__ = "dispatch_run_jobs"
    __table_args__ = (
        UniqueConstraint("dispatch_run_id", "job_id", name="uq_dispatch_run_job"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dispatch_run_id: Mapped[int] = mapped_column(
        ForeignKey("dispatch_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    dispatch_run: Mapped[DispatchRun] = relationship(back_populates="jobs")
    job: Mapped[Job] = relationship(back_populates="dispatch_run_links")


class DispatchRunEmployeeLocation(Base):
    """Per-run snapshot of which location each employee uses."""

    __tablename__ = "dispatch_run_employee_locations"
    __table_args__ = (
        UniqueConstraint("dispatch_run_id", "employee_id", name="uq_dispatch_run_employee"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dispatch_run_id: Mapped[int] = mapped_column(
        ForeignKey("dispatch_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_location_id: Mapped[int] = mapped_column(
        ForeignKey("employee_locations.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    dispatch_run: Mapped[DispatchRun] = relationship(back_populates="employee_locations")
    employee: Mapped[Employee] = relationship(back_populates="run_locations")
    employee_location: Mapped[EmployeeLocation] = relationship(
        back_populates="dispatch_run_snapshots"
    )


class DispatchAssignment(Base, TimestampMixin):
    __tablename__ = "dispatch_assignments"
    __table_args__ = (
        UniqueConstraint(
            "dispatch_run_id", "employee_id", name="uq_dispatch_run_employee_assignment"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dispatch_run_id: Mapped[int] = mapped_column(
        ForeignKey("dispatch_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_skill_id: Mapped[int | None] = mapped_column(
        ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )
    assigned_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    substitution_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    substitution_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    manually_overridden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    warning_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    dispatch_run: Mapped[DispatchRun] = relationship(back_populates="assignments")
    job: Mapped[Job] = relationship(back_populates="dispatch_assignments")
    employee: Mapped[Employee] = relationship(back_populates="dispatch_assignments")
    assigned_skill: Mapped[Skill | None] = relationship(
        "Skill", back_populates="dispatch_assignments"
    )


class DispatchVehicleRoute(Base, TimestampMixin):
    __tablename__ = "dispatch_vehicle_routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dispatch_run_id: Mapped[int] = mapped_column(
        ForeignKey("dispatch_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    driver_employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vehicle_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    route_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    total_duration_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_distance_miles: Mapped[float | None] = mapped_column(Float, nullable=True)
    arrival_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_late: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    google_maps_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    route_geometry_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    warning_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    dispatch_run: Mapped[DispatchRun] = relationship(back_populates="vehicle_routes")
    job: Mapped[Job] = relationship(back_populates="vehicle_routes")
    driver: Mapped[Employee] = relationship(foreign_keys=[driver_employee_id])
    stops: Mapped[list[DispatchRouteStop]] = relationship(
        back_populates="vehicle_route", cascade="all, delete-orphan"
    )


class DispatchRouteStop(Base, TimestampMixin):
    __tablename__ = "dispatch_route_stops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_route_id: Mapped[int] = mapped_column(
        ForeignKey("dispatch_vehicle_routes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stop_order: Mapped[int] = mapped_column(Integer, nullable=False)
    stop_type: Mapped[str] = mapped_column(String(50), nullable=False)
    employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )
    job_id: Mapped[int | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    location_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    eta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ride_time_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)

    vehicle_route: Mapped[DispatchVehicleRoute] = relationship(back_populates="stops")
    employee: Mapped[Employee | None] = relationship(foreign_keys=[employee_id])
    job: Mapped[Job | None] = relationship(back_populates="route_stops")
