"""Employee and location models."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.dispatch import DispatchAssignment, DispatchRunEmployeeLocation
    from app.models.job import JobExcludedEmployee, JobIncludedEmployee
    from app.models.skill import EmployeeSkill


class Employee(Base, TimestampMixin):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_driver: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_supervisor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    default_vehicle_capacity: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    locations: Mapped[list[EmployeeLocation]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    skills: Mapped[list[EmployeeSkill]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    dispatch_assignments: Mapped[list[DispatchAssignment]] = relationship(
        back_populates="employee"
    )
    run_locations: Mapped[list[DispatchRunEmployeeLocation]] = relationship(
        back_populates="employee"
    )
    included_on_jobs: Mapped[list[JobIncludedEmployee]] = relationship(
        back_populates="employee"
    )
    excluded_from_jobs: Mapped[list[JobExcludedEmployee]] = relationship(
        back_populates="employee"
    )


class EmployeeLocation(Base, TimestampMixin):
    __tablename__ = "employee_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    employee: Mapped[Employee] = relationship(back_populates="locations")
    dispatch_run_snapshots: Mapped[list[DispatchRunEmployeeLocation]] = relationship(
        back_populates="employee_location"
    )
