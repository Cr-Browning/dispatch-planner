"""Employee location CRUD."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Employee, EmployeeLocation
from app.schemas.employee import EmployeeLocationCreate, EmployeeLocationUpdate
from app.services.exceptions import NotFoundError


class LocationService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _get_employee(self, employee_id: int) -> Employee:
        employee = self._db.get(Employee, employee_id)
        if employee is None:
            raise NotFoundError("Employee", employee_id)
        return employee

    def get_location(self, employee_id: int, location_id: int) -> EmployeeLocation:
        location = self._db.get(EmployeeLocation, location_id)
        if location is None or location.employee_id != employee_id:
            raise NotFoundError("EmployeeLocation", location_id)
        return location

    def _clear_primary(self, employee_id: int, except_id: int | None = None) -> None:
        stmt = select(EmployeeLocation).where(
            EmployeeLocation.employee_id == employee_id,
            EmployeeLocation.is_primary.is_(True),
        )
        for loc in self._db.scalars(stmt).all():
            if except_id is None or loc.id != except_id:
                loc.is_primary = False

    def create_location(
        self, employee_id: int, data: EmployeeLocationCreate
    ) -> EmployeeLocation:
        self._get_employee(employee_id)
        if data.is_primary:
            self._clear_primary(employee_id)
        location = EmployeeLocation(
            employee_id=employee_id,
            label=data.label.strip(),
            address=data.address.strip(),
            latitude=data.latitude,
            longitude=data.longitude,
            is_primary=data.is_primary,
            notes=data.notes,
        )
        self._db.add(location)
        self._db.commit()
        self._db.refresh(location)
        return location

    def update_location(
        self, employee_id: int, location_id: int, data: EmployeeLocationUpdate
    ) -> EmployeeLocation:
        location = self.get_location(employee_id, location_id)
        if data.label is not None:
            location.label = data.label.strip()
        if data.address is not None:
            location.address = data.address.strip()
        if data.latitude is not None:
            location.latitude = data.latitude
        if data.longitude is not None:
            location.longitude = data.longitude
        if data.notes is not None:
            location.notes = data.notes
        if data.is_primary is True:
            self._clear_primary(employee_id, except_id=location_id)
            location.is_primary = True
        elif data.is_primary is False:
            location.is_primary = False
        self._db.commit()
        self._db.refresh(location)
        return location

    def delete_location(self, employee_id: int, location_id: int) -> None:
        location = self.get_location(employee_id, location_id)
        self._db.delete(location)
        self._db.commit()
