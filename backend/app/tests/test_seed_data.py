"""Phase 5 seed data tests."""

import json

import pytest
from sqlalchemy import func, select

from app.models import (
    AppSetting,
    Employee,
    EmployeeSkill,
    Job,
    JobManualSubstitution,
    JobRequiredSkill,
    OptimizationProfile,
    Skill,
)
from app.seed.seed_data import (
    SEED_DRIVER_COUNT,
    SEED_EMPLOYEE_COUNT,
    SEED_JOB_COUNT,
    SEED_WORKER_COUNT,
    SKILL_NAMES,
    seed_database,
)


@pytest.mark.phase5
def test_seed_creates_full_catalog(db_session) -> None:
    catalog = seed_database(db_session, commit=True)

    assert len(catalog.skills) == len(SKILL_NAMES)
    assert len(catalog.employees) == SEED_EMPLOYEE_COUNT
    assert len(catalog.jobs) == SEED_JOB_COUNT
    assert len(catalog.profiles) == 6

    assert db_session.scalar(select(func.count()).select_from(Skill)) == len(SKILL_NAMES)
    assert db_session.scalar(select(func.count()).select_from(Employee)) == SEED_EMPLOYEE_COUNT
    assert db_session.scalar(select(func.count()).select_from(Job)) == SEED_JOB_COUNT


@pytest.mark.phase5
def test_seed_is_idempotent(db_session) -> None:
    seed_database(db_session, commit=True)
    counts_after_first = {
        "skills": db_session.scalar(select(func.count()).select_from(Skill)),
        "employees": db_session.scalar(select(func.count()).select_from(Employee)),
        "jobs": db_session.scalar(select(func.count()).select_from(Job)),
    }
    seed_database(db_session, commit=True)
    counts_after_second = {
        "skills": db_session.scalar(select(func.count()).select_from(Skill)),
        "employees": db_session.scalar(select(func.count()).select_from(Employee)),
        "jobs": db_session.scalar(select(func.count()).select_from(Job)),
    }
    assert counts_after_first == counts_after_second


@pytest.mark.phase5
def test_three_drivers_and_seven_workers(db_session) -> None:
    catalog = seed_database(db_session, commit=True)
    drivers = [e for e in catalog.employees.values() if e.is_driver]
    workers = [e for e in catalog.employees.values() if not e.is_driver]
    assert len(drivers) == SEED_DRIVER_COUNT
    assert len(workers) == SEED_WORKER_COUNT
    assert len(drivers) >= 3
    assert len(workers) >= 7


@pytest.mark.phase5
def test_vehicle_capacities_four_three_and_five(db_session) -> None:
    catalog = seed_database(db_session, commit=True)
    alex = catalog.employees["alex_driver"]
    morgan = catalog.employees["morgan_lead"]
    riley = catalog.employees["riley_van"]
    assert alex.default_vehicle_capacity == 4
    assert morgan.default_vehicle_capacity == 3
    assert riley.default_vehicle_capacity == 5


@pytest.mark.phase5
def test_taylor_is_only_tile_proficiency_five(db_session) -> None:
    catalog = seed_database(db_session, commit=True)
    tile_skill = catalog.skills["Tile"]

    tile_fives = db_session.scalars(
        select(EmployeeSkill).where(
            EmployeeSkill.skill_id == tile_skill.id,
            EmployeeSkill.proficiency >= 5,
        )
    ).all()
    assert len(tile_fives) == 1
    assert tile_fives[0].employee_id == catalog.employees["taylor_tile"].id


@pytest.mark.phase5
def test_job1_contents_substitutes_for_cleaning(db_session) -> None:
    catalog = seed_database(db_session, commit=True)
    job = catalog.jobs["demo_cleaning"]
    cleaning = catalog.skills["Cleaning"]
    contents = catalog.skills["Contents"]

    sub = db_session.scalars(
        select(JobManualSubstitution).where(JobManualSubstitution.job_id == job.id)
    ).first()
    assert sub is not None
    assert sub.required_skill_id == cleaning.id
    assert sub.substitute_skill_id == contents.id
    assert sub.allowed is True


@pytest.mark.phase5
def test_job_required_and_preferred_skills(db_session) -> None:
    catalog = seed_database(db_session, commit=True)
    job = catalog.jobs["demo_cleaning"]

    rows = db_session.scalars(
        select(JobRequiredSkill).where(JobRequiredSkill.job_id == job.id)
    ).all()
    required = [r for r in rows if not r.is_preferred]
    preferred = [r for r in rows if r.is_preferred]
    assert len(required) == 2
    assert len(preferred) == 1
    assert job.required_headcount == 3


@pytest.mark.phase5
def test_optimization_profiles_include_default(db_session) -> None:
    seed_database(db_session, commit=True)
    default_profiles = db_session.scalars(
        select(OptimizationProfile).where(OptimizationProfile.is_default.is_(True))
    ).all()
    assert len(default_profiles) == 1
    assert default_profiles[0].name == "fewest_vehicles"


@pytest.mark.phase5
def test_export_addresses_hidden_by_default(db_session) -> None:
    seed_database(db_session, commit=True)
    row = db_session.scalars(
        select(AppSetting).where(AppSetting.key == "export_include_addresses")
    ).first()
    assert row is not None
    assert json.loads(row.value_json) is False


@pytest.mark.phase5
def test_seed_catalog_fixture_matches_full_seed(seed_catalog: dict) -> None:
    assert len(seed_catalog["skills"]) == len(SKILL_NAMES)
    assert len(seed_catalog["employees"]) == SEED_EMPLOYEE_COUNT
    assert len(seed_catalog["jobs"]) == SEED_JOB_COUNT
    assert "alex_driver" in seed_catalog["employees"]
    assert "taylor_tile" in seed_catalog["employees"]
    assert "demo_cleaning" in seed_catalog["jobs"]


@pytest.mark.phase5
def test_api_lists_seeded_data(client, auth_headers, db_session) -> None:
    seed_database(db_session, commit=True)

    employees = client.get("/employees", headers=auth_headers)
    skills = client.get("/skills", headers=auth_headers)
    jobs = client.get("/jobs", headers=auth_headers)

    assert employees.status_code == 200
    assert len(employees.json()) == SEED_EMPLOYEE_COUNT
    assert skills.status_code == 200
    assert len(skills.json()) == len(SKILL_NAMES)
    assert jobs.status_code == 200
    assert len(jobs.json()) == SEED_JOB_COUNT
