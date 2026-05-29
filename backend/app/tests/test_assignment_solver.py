"""Assignment solver tests (Phase 9)."""

import pytest

from app.schemas.assignment import AssignmentProblem
from app.services.assignment_solver import AssignmentSolver
from app.services.eligibility_service import EligibilityService
from app.services.scarcity_service import ScarcityService


def _problem(seed_catalog, db_session, job_keys: list[str] | None = None) -> AssignmentProblem:
    eligibility = EligibilityService(db_session)
    employees = eligibility.load_employees()
    if job_keys is None:
        job_keys = list(seed_catalog["jobs"].keys())
    jobs = [eligibility.load_job(seed_catalog["jobs"][k].id) for k in job_keys]
    matrix = eligibility.build_matrix(employees, jobs)
    scarce = ScarcityService(db_session).detect_scarce_skills(
        employees, jobs, eligibility_matrix=matrix
    )
    return AssignmentProblem(
        employees=employees, jobs=jobs, eligibility=matrix, scarce_skills=scarce
    )


@pytest.mark.phase9
def test_one_employee_one_job(seed_catalog, db_session) -> None:
    solution = AssignmentSolver().solve(_problem(seed_catalog, db_session))
    job_by_employee = {a.employee_id: a.job_id for a in solution.assignments}
    assert len(job_by_employee) == len(solution.assignments)


@pytest.mark.phase9
def test_job_headcount_met_when_possible(seed_catalog, db_session) -> None:
    solution = AssignmentSolver().solve(_problem(seed_catalog, db_session))
    job1_id = seed_catalog["jobs"]["demo_cleaning"].id
    count = sum(1 for a in solution.assignments if a.job_id == job1_id)
    assert count >= 3


@pytest.mark.phase9
def test_required_skills_covered(seed_catalog, db_session) -> None:
    solution = AssignmentSolver().solve(_problem(seed_catalog, db_session))
    job1_id = seed_catalog["jobs"]["demo_cleaning"].id
    roles = [a for a in solution.assignments if a.job_id == job1_id]
    skill_ids = {a.assigned_skill_id for a in roles}
    demo_id = seed_catalog["skills"]["Demo"].id
    cleaning_id = seed_catalog["skills"]["Cleaning"].id
    contents_id = seed_catalog["skills"]["Contents"].id
    assert demo_id in skill_ids
    assert cleaning_id in skill_ids or contents_id in skill_ids


@pytest.mark.phase9
def test_taylor_assigned_to_tile_job_not_cleaning(seed_catalog, db_session) -> None:
    solution = AssignmentSolver().solve(_problem(seed_catalog, db_session))
    taylor_id = seed_catalog["employees"]["taylor_tile"].id
    cleaning_id = seed_catalog["jobs"]["demo_cleaning"].id
    tile_id = seed_catalog["jobs"]["flooring_tile"].id
    taylor_job = next((a.job_id for a in solution.assignments if a.employee_id == taylor_id), None)
    assert taylor_job == tile_id
    assert taylor_job != cleaning_id


@pytest.mark.phase9
def test_driver_counts_as_worker(seed_catalog, db_session) -> None:
    solution = AssignmentSolver().solve(_problem(seed_catalog, db_session))
    alex_id = seed_catalog["employees"]["alex_driver"].id
    alex = next((a for a in solution.assignments if a.employee_id == alex_id), None)
    assert alex is not None
    assert alex.assigned_role == "driver"


@pytest.mark.phase9
def test_supervisor_driver_role(seed_catalog, db_session) -> None:
    solution = AssignmentSolver().solve(_problem(seed_catalog, db_session))
    morgan_id = seed_catalog["employees"]["morgan_lead"].id
    morgan = next((a for a in solution.assignments if a.employee_id == morgan_id), None)
    assert morgan is not None
    assert morgan.assigned_role == "driver"


@pytest.mark.phase9
def test_substitution_recorded(seed_catalog, db_session) -> None:
    eligibility = EligibilityService(db_session)
    job1 = eligibility.load_job(seed_catalog["jobs"]["demo_cleaning"].id)
    casey = eligibility.load_employees([seed_catalog["employees"]["casey_contents"].id])[0]
    jamie = eligibility.load_employees([seed_catalog["employees"]["jamie_drywall"].id])[0]
    matrix = eligibility.build_matrix([casey, jamie], [job1])
    problem = AssignmentProblem(
        employees=[casey, jamie],
        jobs=[job1],
        eligibility=matrix,
        scarce_skills=[],
    )
    solution = AssignmentSolver().solve(problem)
    casey_assignment = next(a for a in solution.assignments if a.employee_id == casey.id)
    assert casey_assignment.substitution_used is True


@pytest.mark.phase9
def test_reasoning_summary_not_empty(seed_catalog, db_session) -> None:
    solution = AssignmentSolver().solve(_problem(seed_catalog, db_session))
    assert solution.reasoning_summary
    assert "Assigned" in solution.reasoning_summary


@pytest.mark.phase9
def test_solve_via_api(client, auth_headers, seed_catalog, db_session) -> None:
    job_ids = [
        seed_catalog["jobs"]["demo_cleaning"].id,
        seed_catalog["jobs"]["flooring_tile"].id,
    ]
    create = client.post(
        "/dispatch-runs",
        json={
            "run_date": "2026-06-15",
            "name": "Test Solve Run",
            "job_ids": job_ids,
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    run_id = create.json()["id"]

    solve = client.post(f"/dispatch-runs/{run_id}/solve", headers=auth_headers)
    assert solve.status_code == 200
    body = solve.json()
    assert body["status"] == "reviewed"
    assert len(body["assignments"]) >= 6
    assert body["reasoning_summary"]
