"""ORM model and constraint tests (Phase 2)."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import DispatchRun, DispatchRunEmployeeLocation, Job, OptimizationProfile
from app.tests import factories


@pytest.mark.phase2
def test_dispatch_run_employee_location_unique(db_session) -> None:
    employee = factories.create_employee(db_session, first_name="A", last_name="B")
    loc1 = factories.create_location(db_session, employee, label="Home")
    loc2 = factories.create_location(
        db_session, employee, label="Shop", address="2 Shop Rd", is_primary=False
    )
    profile = OptimizationProfile(
        name="fewest_vehicles",
        objective_order_json='["fewest_vehicles"]',
        is_default=True,
    )
    db_session.add_all([employee, profile])
    db_session.flush()

    run = DispatchRun(
        run_date=datetime.now(UTC).date(),
        name="Test Run",
        optimization_profile_id=profile.id,
        status="draft",
    )
    db_session.add(run)
    db_session.flush()

    db_session.add(
        DispatchRunEmployeeLocation(
            dispatch_run_id=run.id,
            employee_id=employee.id,
            employee_location_id=loc1.id,
        )
    )
    db_session.commit()

    duplicate = DispatchRunEmployeeLocation(
        dispatch_run_id=run.id,
        employee_id=employee.id,
        employee_location_id=loc2.id,
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()


@pytest.mark.phase2
def test_job_with_required_skill(db_session) -> None:
    skill = factories.create_skill(db_session, name="Tile")
    job = factories.create_job(db_session, job_name="Tile Job")
    factories.add_job_required_skill(
        db_session, job, skill, minimum_proficiency=4, is_preferred=False
    )
    db_session.commit()

    loaded = db_session.get(Job, job.id)
    assert loaded is not None
    assert len(loaded.required_skills) == 1
    assert loaded.required_skills[0].minimum_proficiency == 4
