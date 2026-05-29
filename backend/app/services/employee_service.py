"""Employee and employee-skill CRUD."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import Employee, EmployeeSkill, Skill
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeSkillCreate,
    EmployeeSkillUpdate,
    EmployeeSkillResponse,
    EmployeeUpdate,
)
from app.services.exceptions import ConflictError, NotFoundError
from app.services.skill_service import SkillService


class EmployeeService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._skills = SkillService(db)

    def _base_query(self):
        return select(Employee).options(
            selectinload(Employee.locations),
            selectinload(Employee.skills).selectinload(EmployeeSkill.skill),
        )

    def list_employees(self, *, active_only: bool = False) -> list[Employee]:
        stmt = self._base_query().order_by(Employee.last_name, Employee.first_name)
        if active_only:
            stmt = stmt.where(Employee.active.is_(True))
        return list(self._db.scalars(stmt).unique().all())

    def get_employee(self, employee_id: int) -> Employee:
        employee = self._db.scalars(
            self._base_query().where(Employee.id == employee_id)
        ).first()
        if employee is None:
            raise NotFoundError("Employee", employee_id)
        return employee

    def create_employee(self, data: EmployeeCreate) -> Employee:
        employee = Employee(
            first_name=data.first_name.strip(),
            last_name=data.last_name.strip(),
            display_name=data.display_name.strip() if data.display_name else None,
            active=data.active,
            is_driver=data.is_driver,
            is_supervisor=data.is_supervisor,
            default_vehicle_capacity=data.default_vehicle_capacity,
            phone=data.phone.strip() if data.phone else None,
            notes=data.notes,
        )
        self._db.add(employee)
        self._db.commit()
        self._db.refresh(employee)
        return self.get_employee(employee.id)

    def update_employee(self, employee_id: int, data: EmployeeUpdate) -> Employee:
        employee = self.get_employee(employee_id)
        if data.first_name is not None:
            employee.first_name = data.first_name.strip()
        if data.last_name is not None:
            employee.last_name = data.last_name.strip()
        if data.display_name is not None:
            employee.display_name = data.display_name.strip() or None
        if data.active is not None:
            employee.active = data.active
        if data.is_driver is not None:
            employee.is_driver = data.is_driver
        if data.is_supervisor is not None:
            employee.is_supervisor = data.is_supervisor
        if data.default_vehicle_capacity is not None:
            employee.default_vehicle_capacity = data.default_vehicle_capacity
        if data.phone is not None:
            employee.phone = data.phone.strip() or None
        if data.notes is not None:
            employee.notes = data.notes
        self._db.commit()
        return self.get_employee(employee_id)

    def delete_employee(self, employee_id: int) -> None:
        employee = self.get_employee(employee_id)
        self._db.delete(employee)
        self._db.commit()

    def add_skill(self, employee_id: int, data: EmployeeSkillCreate) -> EmployeeSkill:
        self.get_employee(employee_id)
        self._skills.get_skill(data.skill_id)
        existing = self._db.scalars(
            select(EmployeeSkill).where(
                EmployeeSkill.employee_id == employee_id,
                EmployeeSkill.skill_id == data.skill_id,
            )
        ).first()
        if existing is not None:
            raise ConflictError("Employee already has this skill; use PUT to update proficiency")
        row = EmployeeSkill(
            employee_id=employee_id,
            skill_id=data.skill_id,
            proficiency=data.proficiency,
        )
        self._db.add(row)
        try:
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            raise ConflictError("Invalid employee skill data") from exc
        self._db.refresh(row)
        return self._attach_skill(row)

    def update_skill(
        self, employee_id: int, skill_id: int, data: EmployeeSkillUpdate
    ) -> EmployeeSkill:
        row = self._db.scalars(
            select(EmployeeSkill).where(
                EmployeeSkill.employee_id == employee_id,
                EmployeeSkill.skill_id == skill_id,
            )
        ).first()
        if row is None:
            raise NotFoundError("EmployeeSkill", skill_id)
        row.proficiency = data.proficiency
        self._db.commit()
        self._db.refresh(row)
        return self._attach_skill(row)

    def remove_skill(self, employee_id: int, skill_id: int) -> None:
        row = self._db.scalars(
            select(EmployeeSkill).where(
                EmployeeSkill.employee_id == employee_id,
                EmployeeSkill.skill_id == skill_id,
            )
        ).first()
        if row is None:
            raise NotFoundError("EmployeeSkill", skill_id)
        self._db.delete(row)
        self._db.commit()

    def _attach_skill(self, row: EmployeeSkill) -> EmployeeSkill:
        row.skill = self._skills.get_skill(row.skill_id)
        return row

    @staticmethod
    def skill_to_response(row: EmployeeSkill) -> EmployeeSkillResponse:
        skill_name = row.skill.name if row.skill else None
        return EmployeeSkillResponse(
            id=row.id,
            employee_id=row.employee_id,
            skill_id=row.skill_id,
            proficiency=row.proficiency,
            skill_name=skill_name,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
