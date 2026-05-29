"""Eligibility filtering tests (Phase 8)."""

import pytest

from app.services.eligibility_service import EligibilityService


@pytest.fixture
def eligibility(db_session) -> EligibilityService:
    return EligibilityService(db_session)


@pytest.mark.phase8
def test_inactive_employee_excluded(eligibility: EligibilityService, seed_catalog, db_session) -> None:
    job = eligibility.load_job(seed_catalog["jobs"]["demo_cleaning"].id)
    employee = eligibility.load_employees([seed_catalog["employees"]["chris_cleaner"].id])[0]
    employee.active = False
    db_session.commit()

    result = eligibility.evaluate(employee, job)
    assert result.eligible is False
    assert any("inactive" in r.lower() for r in result.reasons)


@pytest.mark.phase8
def test_excluded_employee_not_eligible(
    eligibility: EligibilityService, seed_catalog, db_session
) -> None:
    from app.models import JobExcludedEmployee

    job = eligibility.load_job(seed_catalog["jobs"]["demo_cleaning"].id)
    taylor = eligibility.load_employees([seed_catalog["employees"]["taylor_tile"].id])[0]
    db_session.add(JobExcludedEmployee(job_id=job.id, employee_id=taylor.id))
    db_session.commit()
    job = eligibility.load_job(job.id)

    result = eligibility.evaluate(taylor, job)
    assert result.eligible is False
    assert any("excluded" in r.lower() for r in result.reasons)


@pytest.mark.phase8
def test_must_include_eligible_with_warning(
    eligibility: EligibilityService, seed_catalog, db_session
) -> None:
    from app.models import JobIncludedEmployee

    job = eligibility.load_job(seed_catalog["jobs"]["flooring_tile"].id)
    jamie = eligibility.load_employees([seed_catalog["employees"]["jamie_drywall"].id])[0]
    db_session.add(JobIncludedEmployee(job_id=job.id, employee_id=jamie.id))
    db_session.commit()
    job = eligibility.load_job(job.id)

    result = eligibility.evaluate(jamie, job)
    assert result.eligible is True
    assert result.is_must_include is True
    assert any("Must-include" in w for w in result.warnings)


@pytest.mark.phase8
def test_direct_skill_match(eligibility: EligibilityService, seed_catalog) -> None:
    job = eligibility.load_job(seed_catalog["jobs"]["demo_cleaning"].id)
    chris = eligibility.load_employees([seed_catalog["employees"]["chris_cleaner"].id])[0]
    result = eligibility.evaluate(chris, job)
    assert result.eligible is True
    assert any(m.match_type == "direct" and m.required_skill_name == "Cleaning" for m in result.skill_matches)


@pytest.mark.phase8
def test_substitution_only_when_enabled(eligibility: EligibilityService, seed_catalog) -> None:
    job = eligibility.load_job(seed_catalog["jobs"]["demo_cleaning"].id)
    casey = eligibility.load_employees([seed_catalog["employees"]["casey_contents"].id])[0]
    result = eligibility.evaluate(casey, job)
    assert result.eligible is True
    sub_matches = [m for m in result.skill_matches if m.match_type == "substitution"]
    assert len(sub_matches) >= 1
    assert sub_matches[0].required_skill_name == "Cleaning"
    assert sub_matches[0].skill_name == "Contents"


@pytest.mark.phase8
def test_no_substitution_without_manual_rule(
    eligibility: EligibilityService, seed_catalog, db_session
) -> None:
    job = eligibility.load_job(seed_catalog["jobs"]["flooring_tile"].id)
    casey = eligibility.load_employees([seed_catalog["employees"]["casey_contents"].id])[0]
    result = eligibility.evaluate(casey, job)
    assert not any(m.match_type == "substitution" for m in result.skill_matches)
    # Casey may still be eligible via preferred General labor on this job
    assert all(m.match_type == "direct" for m in result.skill_matches)


@pytest.mark.phase8
def test_driver_flag_separate_from_skills(eligibility: EligibilityService, seed_catalog) -> None:
    alex = eligibility.load_employees([seed_catalog["employees"]["alex_driver"].id])[0]
    assert alex.is_driver is True
    assert not any(es.skill and es.skill.name == "Driver" for es in alex.skills)
