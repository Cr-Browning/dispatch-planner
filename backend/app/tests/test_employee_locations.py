"""Employee location tests (Phase 4)."""

import pytest
from sqlalchemy import select

from app.models import EmployeeLocation
from app.services.location_service import LocationService
from app.tests import factories


@pytest.mark.phase4
def test_employee_can_have_multiple_locations(db_session) -> None:
    employee = factories.create_employee(db_session)
    factories.create_location(db_session, employee, label="Home", is_primary=True)
    factories.create_location(db_session, employee, label="Shop", is_primary=False)
    db_session.commit()

    locations = list(
        db_session.scalars(
            select(EmployeeLocation).where(EmployeeLocation.employee_id == employee.id)
        ).all()
    )
    assert len(locations) == 2


@pytest.mark.phase4
def test_setting_primary_clears_other_primaries(db_session) -> None:
    employee = factories.create_employee(db_session)
    home = factories.create_location(db_session, employee, label="Home", is_primary=True)
    shop = factories.create_location(db_session, employee, label="Shop", is_primary=False)
    db_session.commit()

    from app.schemas.employee import EmployeeLocationUpdate

    service = LocationService(db_session)
    service.update_location(employee.id, shop.id, EmployeeLocationUpdate(is_primary=True))
    db_session.refresh(home)
    db_session.refresh(shop)
    assert home.is_primary is False
    assert shop.is_primary is True
