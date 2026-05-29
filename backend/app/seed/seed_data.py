"""Idempotent seed data — safe to run multiple times."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AppSetting,
    Employee,
    EmployeeLocation,
    EmployeeSkill,
    Job,
    JobManualSubstitution,
    JobRequiredSkill,
    OptimizationProfile,
    Skill,
)

# Fake Philadelphia-area coordinates (easy to change)
BASE_LAT = 39.9526
BASE_LNG = -75.1652

SKILL_NAMES: list[str] = [
    "Demo",
    "Drywall",
    "Framing",
    "Flooring",
    "Tile",
    "Painting",
    "Cleaning",
    "Contents",
    "Mitigation",
    "Roofing",
    "Electrical",
    "Plumbing",
    "HVAC",
    "General labor",
]

OPTIMIZATION_PROFILES: list[dict[str, Any]] = [
    {
        "name": "fewest_vehicles",
        "objective_order": [
            "fewest_vehicles",
            "shortest_drive_time",
            "least_mileage",
            "preserve_scarce_skills",
        ],
        "is_default": True,
    },
    {
        "name": "closest_eligible_workers",
        "objective_order": ["closest_eligible_workers", "skill_match"],
        "is_default": False,
    },
    {
        "name": "best_skilled_workers",
        "objective_order": ["skill_match", "preserve_scarce_skills"],
        "is_default": False,
    },
    {
        "name": "balanced_skill_distance",
        "objective_order": ["balanced_skill_distance"],
        "is_default": False,
    },
    {
        "name": "fastest_route",
        "objective_order": ["shortest_drive_time", "fewest_vehicles"],
        "is_default": False,
    },
    {
        "name": "lowest_mileage",
        "objective_order": ["least_mileage", "fewest_vehicles"],
        "is_default": False,
    },
]

EMPLOYEE_FIXTURES: list[dict[str, Any]] = [
    {
        "key": "alex_driver",
        "display_name": "Alex Driver",
        "first_name": "Alex",
        "last_name": "Driver",
        "phone": "215-555-0101",
        "is_driver": True,
        "is_supervisor": False,
        "default_vehicle_capacity": 4,
        "skills": [("Demo", 3), ("General labor", 4)],
        "location": {
            "label": "Home",
            "address": "1200 Chestnut St, Philadelphia, PA",
            "latitude": BASE_LAT + 0.01,
            "longitude": BASE_LNG - 0.01,
        },
    },
    {
        "key": "morgan_lead",
        "display_name": "Morgan Lead",
        "first_name": "Morgan",
        "last_name": "Lead",
        "phone": "215-555-0102",
        "is_driver": True,
        "is_supervisor": True,
        "default_vehicle_capacity": 3,
        "skills": [("Flooring", 4), ("General labor", 3)],
        "location": {
            "label": "Home",
            "address": "1300 Market St, Philadelphia, PA",
            "latitude": BASE_LAT + 0.008,
            "longitude": BASE_LNG - 0.008,
        },
    },
    {
        "key": "jamie_drywall",
        "display_name": "Jamie Drywall",
        "first_name": "Jamie",
        "last_name": "Drywall",
        "is_driver": False,
        "is_supervisor": False,
        "default_vehicle_capacity": 4,
        "skills": [("Drywall", 4), ("Painting", 3)],
        "location": {
            "label": "Home",
            "address": "1400 Walnut St, Philadelphia, PA",
            "latitude": BASE_LAT + 0.006,
            "longitude": BASE_LNG - 0.006,
        },
    },
    {
        "key": "chris_cleaner",
        "display_name": "Chris Cleaner",
        "first_name": "Chris",
        "last_name": "Cleaner",
        "is_driver": False,
        "is_supervisor": False,
        "default_vehicle_capacity": 4,
        "skills": [("Demo", 3), ("Cleaning", 4)],
        "location": {
            "label": "Home",
            "address": "1500 Spruce St, Philadelphia, PA",
            "latitude": BASE_LAT + 0.004,
            "longitude": BASE_LNG - 0.004,
        },
    },
    {
        "key": "taylor_tile",
        "display_name": "Taylor Tile",
        "first_name": "Taylor",
        "last_name": "Tile",
        "is_driver": False,
        "is_supervisor": False,
        "default_vehicle_capacity": 4,
        "skills": [("Tile", 5), ("Flooring", 3)],
        "location": {
            "label": "Home",
            "address": "1600 Locust St, Philadelphia, PA",
            "latitude": BASE_LAT + 0.002,
            "longitude": BASE_LNG - 0.002,
        },
    },
    {
        "key": "casey_contents",
        "display_name": "Casey Contents",
        "first_name": "Casey",
        "last_name": "Contents",
        "is_driver": False,
        "is_supervisor": False,
        "default_vehicle_capacity": 4,
        "skills": [("General labor", 3), ("Contents", 4)],
        "location": {
            "label": "Home",
            "address": "1700 Arch St, Philadelphia, PA",
            "latitude": BASE_LAT,
            "longitude": BASE_LNG,
        },
    },
    {
        "key": "riley_van",
        "display_name": "Riley Van",
        "first_name": "Riley",
        "last_name": "Van",
        "phone": "215-555-0103",
        "is_driver": True,
        "is_supervisor": False,
        "default_vehicle_capacity": 5,
        "skills": [("Framing", 3), ("General labor", 4)],
        "location": {
            "label": "Home",
            "address": "1800 Filbert St, Philadelphia, PA",
            "latitude": BASE_LAT - 0.002,
            "longitude": BASE_LNG - 0.012,
        },
    },
    {
        "key": "pat_paint",
        "display_name": "Pat Paint",
        "first_name": "Pat",
        "last_name": "Paint",
        "is_driver": False,
        "is_supervisor": False,
        "default_vehicle_capacity": 4,
        "skills": [("Painting", 4), ("Drywall", 2), ("Roofing", 3)],
        "location": {
            "label": "Home",
            "address": "1900 Spring Garden St, Philadelphia, PA",
            "latitude": BASE_LAT + 0.012,
            "longitude": BASE_LNG + 0.002,
        },
    },
    {
        "key": "sam_framing",
        "display_name": "Sam Framing",
        "first_name": "Sam",
        "last_name": "Framing",
        "is_driver": False,
        "is_supervisor": False,
        "default_vehicle_capacity": 4,
        "skills": [("Framing", 4), ("Demo", 2)],
        "location": {
            "label": "Home",
            "address": "2000 Spring Garden St, Philadelphia, PA",
            "latitude": BASE_LAT + 0.014,
            "longitude": BASE_LNG + 0.004,
        },
    },
    {
        "key": "drew_mitigation",
        "display_name": "Drew Mitigation",
        "first_name": "Drew",
        "last_name": "Mitigation",
        "is_driver": False,
        "is_supervisor": False,
        "default_vehicle_capacity": 4,
        "skills": [("Mitigation", 4), ("General labor", 3)],
        "location": {
            "label": "Home",
            "address": "2100 Callowhill St, Philadelphia, PA",
            "latitude": BASE_LAT + 0.016,
            "longitude": BASE_LNG + 0.006,
        },
    },
]

JOB_FIXTURES: list[dict[str, Any]] = [
    {
        "key": "demo_cleaning",
        "job_name": "Demo and Cleaning Job",
        "client_name": "Sample Client A",
        "address": "2000 Benjamin Franklin Pkwy, Philadelphia, PA",
        "latitude": BASE_LAT - 0.005,
        "longitude": BASE_LNG + 0.005,
        "required_arrival_time": datetime(2026, 6, 15, 8, 0, tzinfo=UTC),
        "required_headcount": 3,
        "required_skills": [
            {"skill": "Demo", "quantity": 1, "min_proficiency": 1, "preferred": False},
            {"skill": "Cleaning", "quantity": 1, "min_proficiency": 1, "preferred": False},
        ],
        "preferred_skills": [
            {"skill": "General labor", "quantity": 1, "min_proficiency": 1, "preferred": True},
        ],
        "substitutions": [
            {"required_skill": "Cleaning", "substitute_skill": "Contents"},
        ],
    },
    {
        "key": "flooring_tile",
        "job_name": "Flooring and Tile Job",
        "client_name": "Sample Client B",
        "address": "2100 Race St, Philadelphia, PA",
        "latitude": BASE_LAT - 0.008,
        "longitude": BASE_LNG + 0.008,
        "required_arrival_time": datetime(2026, 6, 15, 9, 0, tzinfo=UTC),
        "required_headcount": 3,
        "required_skills": [
            {"skill": "Tile", "quantity": 1, "min_proficiency": 1, "preferred": False},
            {"skill": "Flooring", "quantity": 1, "min_proficiency": 1, "preferred": False},
        ],
        "preferred_skills": [
            {"skill": "General labor", "quantity": 1, "min_proficiency": 1, "preferred": True},
        ],
        "substitutions": [],
    },
    {
        "key": "mitigation_large",
        "job_name": "Large Mitigation Job",
        "client_name": "Sample Client C",
        "address": "2200 Market St, Philadelphia, PA",
        "latitude": BASE_LAT - 0.01,
        "longitude": BASE_LNG + 0.01,
        "required_arrival_time": datetime(2026, 6, 15, 10, 0, tzinfo=UTC),
        "required_headcount": 6,
        "required_skills": [
            {"skill": "Mitigation", "quantity": 2, "min_proficiency": 1, "preferred": False},
        ],
        "preferred_skills": [
            {"skill": "General labor", "quantity": 2, "min_proficiency": 1, "preferred": True},
        ],
        "substitutions": [],
    },
    {
        "key": "roof_repair",
        "job_name": "Roof Repair Job",
        "client_name": "Sample Client D",
        "address": "2300 South St, Philadelphia, PA",
        "latitude": BASE_LAT - 0.012,
        "longitude": BASE_LNG + 0.012,
        "required_arrival_time": datetime(2026, 6, 15, 11, 0, tzinfo=UTC),
        "required_headcount": 2,
        "required_skills": [
            {"skill": "Roofing", "quantity": 1, "min_proficiency": 1, "preferred": False},
        ],
        "preferred_skills": [
            {"skill": "General labor", "quantity": 1, "min_proficiency": 1, "preferred": True},
        ],
        "substitutions": [],
    },
]

# Catalog size constants for tests
SEED_EMPLOYEE_COUNT = len(EMPLOYEE_FIXTURES)
SEED_DRIVER_COUNT = sum(1 for e in EMPLOYEE_FIXTURES if e["is_driver"])
SEED_WORKER_COUNT = SEED_EMPLOYEE_COUNT - SEED_DRIVER_COUNT
SEED_JOB_COUNT = len(JOB_FIXTURES)


@dataclass
class SeedCatalog:
    skills: dict[str, Skill]
    employees: dict[str, Employee]
    jobs: dict[str, Job]
    profiles: dict[str, OptimizationProfile]


def _get_or_create_skill(session: Session, name: str) -> Skill:
    skill = session.scalars(select(Skill).where(Skill.name == name)).first()
    if skill is None:
        skill = Skill(name=name, active=True)
        session.add(skill)
        session.flush()
    else:
        skill.active = True
    return skill


def _get_or_create_employee(session: Session, fixture: dict[str, Any]) -> Employee:
    employee = session.scalars(
        select(Employee).where(Employee.display_name == fixture["display_name"])
    ).first()
    if employee is None:
        employee = Employee(
            first_name=fixture["first_name"],
            last_name=fixture["last_name"],
            display_name=fixture["display_name"],
            phone=fixture.get("phone"),
            active=True,
            is_driver=fixture["is_driver"],
            is_supervisor=fixture["is_supervisor"],
            default_vehicle_capacity=fixture["default_vehicle_capacity"],
        )
        session.add(employee)
        session.flush()
    else:
        employee.first_name = fixture["first_name"]
        employee.last_name = fixture["last_name"]
        if fixture.get("phone"):
            employee.phone = fixture["phone"]
        employee.is_driver = fixture["is_driver"]
        employee.is_supervisor = fixture["is_supervisor"]
        employee.default_vehicle_capacity = fixture["default_vehicle_capacity"]
        employee.active = True
    return employee


def _ensure_employee_skill(
    session: Session, employee: Employee, skill: Skill, proficiency: int
) -> EmployeeSkill:
    row = session.scalars(
        select(EmployeeSkill).where(
            EmployeeSkill.employee_id == employee.id,
            EmployeeSkill.skill_id == skill.id,
        )
    ).first()
    if row is None:
        row = EmployeeSkill(
            employee_id=employee.id, skill_id=skill.id, proficiency=proficiency
        )
        session.add(row)
    else:
        row.proficiency = proficiency
    session.flush()
    return row


def _ensure_primary_location(session: Session, employee: Employee, loc: dict[str, Any]) -> None:
    location = session.scalars(
        select(EmployeeLocation).where(
            EmployeeLocation.employee_id == employee.id,
            EmployeeLocation.label == loc["label"],
        )
    ).first()
    if location is None:
        location = EmployeeLocation(
            employee_id=employee.id,
            label=loc["label"],
            address=loc["address"],
            latitude=loc["latitude"],
            longitude=loc["longitude"],
            is_primary=True,
        )
        session.add(location)
    else:
        location.address = loc["address"]
        location.latitude = loc["latitude"]
        location.longitude = loc["longitude"]
        location.is_primary = True
    session.flush()
    # Clear other primaries
    others = session.scalars(
        select(EmployeeLocation).where(
            EmployeeLocation.employee_id == employee.id,
            EmployeeLocation.id != location.id,
        )
    ).all()
    for other in others:
        other.is_primary = False


def _get_or_create_job(session: Session, fixture: dict[str, Any]) -> Job:
    job = session.scalars(select(Job).where(Job.job_name == fixture["job_name"])).first()
    if job is None:
        job = Job(
            job_name=fixture["job_name"],
            client_name=fixture.get("client_name"),
            address=fixture["address"],
            latitude=fixture["latitude"],
            longitude=fixture["longitude"],
            required_arrival_time=fixture["required_arrival_time"],
            required_headcount=fixture["required_headcount"],
            tolls_allowed=True,
            return_trip_enabled=False,
            dropoff_return_enabled=False,
        )
        session.add(job)
        session.flush()
    else:
        job.client_name = fixture.get("client_name")
        job.address = fixture["address"]
        job.latitude = fixture["latitude"]
        job.longitude = fixture["longitude"]
        job.required_arrival_time = fixture["required_arrival_time"]
        job.required_headcount = fixture["required_headcount"]
    return job


def _ensure_job_required_skill(
    session: Session,
    job: Job,
    skill: Skill,
    *,
    required_quantity: int,
    minimum_proficiency: int,
    is_preferred: bool,
) -> JobRequiredSkill:
    row = session.scalars(
        select(JobRequiredSkill).where(
            JobRequiredSkill.job_id == job.id,
            JobRequiredSkill.skill_id == skill.id,
            JobRequiredSkill.is_preferred == is_preferred,
        )
    ).first()
    if row is None:
        row = JobRequiredSkill(
            job_id=job.id,
            skill_id=skill.id,
            required_quantity=required_quantity,
            minimum_proficiency=minimum_proficiency,
            is_preferred=is_preferred,
        )
        session.add(row)
    else:
        row.required_quantity = required_quantity
        row.minimum_proficiency = minimum_proficiency
    session.flush()
    return row


def _ensure_substitution(
    session: Session,
    job: Job,
    required_skill: Skill,
    substitute_skill: Skill,
) -> JobManualSubstitution:
    row = session.scalars(
        select(JobManualSubstitution).where(
            JobManualSubstitution.job_id == job.id,
            JobManualSubstitution.required_skill_id == required_skill.id,
            JobManualSubstitution.substitute_skill_id == substitute_skill.id,
        )
    ).first()
    if row is None:
        row = JobManualSubstitution(
            job_id=job.id,
            required_skill_id=required_skill.id,
            substitute_skill_id=substitute_skill.id,
            allowed=True,
            notes="Contents may substitute for Cleaning",
        )
        session.add(row)
    else:
        row.allowed = True
    session.flush()
    return row


def _seed_optimization_profiles(session: Session) -> dict[str, OptimizationProfile]:
    profiles: dict[str, OptimizationProfile] = {}
    for spec in OPTIMIZATION_PROFILES:
        profile = session.scalars(
            select(OptimizationProfile).where(OptimizationProfile.name == spec["name"])
        ).first()
        objective_json = json.dumps(spec["objective_order"])
        if profile is None:
            profile = OptimizationProfile(
                name=spec["name"],
                objective_order_json=objective_json,
                is_default=spec["is_default"],
            )
            session.add(profile)
        else:
            profile.objective_order_json = objective_json
            profile.is_default = spec["is_default"]
        session.flush()
        profiles[spec["name"]] = profile
    return profiles


def _seed_app_settings(session: Session) -> None:
    settings_to_ensure = {
        "export_include_addresses": False,
    }
    for key, value in settings_to_ensure.items():
        row = session.scalars(select(AppSetting).where(AppSetting.key == key)).first()
        payload = json.dumps(value)
        if row is None:
            session.add(AppSetting(key=key, value_json=payload))
        else:
            row.value_json = payload


def seed_database(session: Session, *, commit: bool = True) -> SeedCatalog:
    """Load full seed catalog idempotently."""
    skills = {name: _get_or_create_skill(session, name) for name in SKILL_NAMES}

    employees: dict[str, Employee] = {}
    for fixture in EMPLOYEE_FIXTURES:
        employee = _get_or_create_employee(session, fixture)
        for skill_name, proficiency in fixture["skills"]:
            _ensure_employee_skill(session, employee, skills[skill_name], proficiency)
        _ensure_primary_location(session, employee, fixture["location"])
        employees[fixture["key"]] = employee

    jobs: dict[str, Job] = {}
    for fixture in JOB_FIXTURES:
        job = _get_or_create_job(session, fixture)
        for req in fixture["required_skills"]:
            _ensure_job_required_skill(
                session,
                job,
                skills[req["skill"]],
                required_quantity=req["quantity"],
                minimum_proficiency=req["min_proficiency"],
                is_preferred=req["preferred"],
            )
        for pref in fixture.get("preferred_skills", []):
            _ensure_job_required_skill(
                session,
                job,
                skills[pref["skill"]],
                required_quantity=pref["quantity"],
                minimum_proficiency=pref["min_proficiency"],
                is_preferred=True,
            )
        for sub in fixture.get("substitutions", []):
            _ensure_substitution(
                session,
                job,
                skills[sub["required_skill"]],
                skills[sub["substitute_skill"]],
            )
        jobs[fixture["key"]] = job

    profiles = _seed_optimization_profiles(session)
    _seed_app_settings(session)

    if commit:
        session.commit()

    return SeedCatalog(skills=skills, employees=employees, jobs=jobs, profiles=profiles)


def main() -> None:
    from app.core.database import SessionLocal, init_db

    init_db()
    with SessionLocal() as session:
        catalog = seed_database(session)
    print("Seed complete.")
    print(f"  Skills: {len(catalog.skills)}")
    print(f"  Employees: {len(catalog.employees)}")
    print(f"  Jobs: {len(catalog.jobs)}")
    print(f"  Optimization profiles: {len(catalog.profiles)}")


if __name__ == "__main__":
    main()


