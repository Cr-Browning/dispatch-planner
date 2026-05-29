"""Job template and requirement models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.dispatch import (
        DispatchAssignment,
        DispatchRunJob,
        DispatchRouteStop,
        DispatchVehicleRoute,
    )
    from app.models.employee import Employee
    from app.models.skill import Skill


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    client_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    required_arrival_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    required_headcount: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    tolls_allowed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    return_trip_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dropoff_return_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    required_skills: Mapped[list[JobRequiredSkill]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    manual_substitutions: Mapped[list[JobManualSubstitution]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    included_employees: Mapped[list[JobIncludedEmployee]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    excluded_employees: Mapped[list[JobExcludedEmployee]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    dispatch_run_links: Mapped[list[DispatchRunJob]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    dispatch_assignments: Mapped[list[DispatchAssignment]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    vehicle_routes: Mapped[list[DispatchVehicleRoute]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    route_stops: Mapped[list[DispatchRouteStop]] = relationship(
        back_populates="job", passive_deletes=True
    )


class JobRequiredSkill(Base, TimestampMixin):
    __tablename__ = "job_required_skills"
    __table_args__ = (
        CheckConstraint(
            "minimum_proficiency >= 1 AND minimum_proficiency <= 5",
            name="ck_job_min_proficiency",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    required_quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    minimum_proficiency: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_preferred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    job: Mapped[Job] = relationship(back_populates="required_skills")
    skill: Mapped[Skill] = relationship(back_populates="job_requirements")


class JobManualSubstitution(Base, TimestampMixin):
    __tablename__ = "job_manual_substitutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    required_skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    substitute_skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    allowed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped[Job] = relationship(back_populates="manual_substitutions")
    required_skill: Mapped[Skill] = relationship(
        back_populates="substitutions_as_required",
        foreign_keys=[required_skill_id],
    )
    substitute_skill: Mapped[Skill] = relationship(
        back_populates="substitutions_as_substitute",
        foreign_keys=[substitute_skill_id],
    )


class JobIncludedEmployee(Base):
    __tablename__ = "job_included_employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job: Mapped[Job] = relationship(back_populates="included_employees")
    employee: Mapped[Employee] = relationship(back_populates="included_on_jobs")


class JobExcludedEmployee(Base):
    __tablename__ = "job_excluded_employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job: Mapped[Job] = relationship(back_populates="excluded_employees")
    employee: Mapped[Employee] = relationship(back_populates="excluded_from_jobs")
