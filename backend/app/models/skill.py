"""Skill catalog and employee skill proficiency."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.dispatch import DispatchAssignment
    from app.models.employee import Employee
    from app.models.job import JobManualSubstitution, JobRequiredSkill


class Skill(Base, TimestampMixin):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    employee_skills: Mapped[list[EmployeeSkill]] = relationship(back_populates="skill")
    job_requirements: Mapped[list[JobRequiredSkill]] = relationship(back_populates="skill")
    substitutions_as_required: Mapped[list[JobManualSubstitution]] = relationship(
        back_populates="required_skill",
        foreign_keys="JobManualSubstitution.required_skill_id",
    )
    substitutions_as_substitute: Mapped[list[JobManualSubstitution]] = relationship(
        back_populates="substitute_skill",
        foreign_keys="JobManualSubstitution.substitute_skill_id",
    )
    dispatch_assignments: Mapped[list[DispatchAssignment]] = relationship(
        back_populates="assigned_skill"
    )


class EmployeeSkill(Base, TimestampMixin):
    __tablename__ = "employee_skills"
    __table_args__ = (
        UniqueConstraint("employee_id", "skill_id", name="uq_employee_skill"),
        CheckConstraint("proficiency >= 1 AND proficiency <= 5", name="ck_proficiency_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    proficiency: Mapped[int] = mapped_column(Integer, nullable=False)

    employee: Mapped[Employee] = relationship(back_populates="skills")
    skill: Mapped[Skill] = relationship(back_populates="employee_skills")
