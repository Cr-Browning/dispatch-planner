"""Employee and skill model/service tests (Phase 4)."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import EmployeeSkill
from app.tests import factories


@pytest.mark.phase4
def test_employee_can_have_multiple_skills(db_session) -> None:
    employee = factories.create_employee(db_session)
    demo = factories.create_skill(db_session, name="Demo")
    paint = factories.create_skill(db_session, name="Painting")
    factories.add_employee_skill(db_session, employee, demo, 3)
    factories.add_employee_skill(db_session, employee, paint, 2)
    db_session.commit()

    db_session.refresh(employee)
    assert len(employee.skills) == 2


@pytest.mark.phase4
def test_proficiency_must_be_1_to_5(db_session) -> None:
    employee = factories.create_employee(db_session)
    skill = factories.create_skill(db_session, name="Tile")
    db_session.commit()

    invalid = EmployeeSkill(employee_id=employee.id, skill_id=skill.id, proficiency=6)
    db_session.add(invalid)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


@pytest.mark.phase4
def test_driver_and_supervisor_are_employee_flags_not_skills(
    db_session, employee_factory
) -> None:
    driver_super = employee_factory(
        first_name="Morgan",
        last_name="Lead",
        is_driver=True,
        is_supervisor=True,
    )
    assert driver_super.is_driver is True
    assert driver_super.is_supervisor is True
    assert len(driver_super.skills) == 0
