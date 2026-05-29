"""Scarcity detection tests (Phase 8)."""

import pytest

from app.services.eligibility_service import EligibilityService
from app.services.scarcity_service import ScarcityService


@pytest.fixture
def scarcity(db_session) -> ScarcityService:
    return ScarcityService(db_session)


@pytest.mark.phase8
def test_no_scarcity_for_single_job(scarcity: ScarcityService, seed_catalog, db_session) -> None:
    eligibility = EligibilityService(db_session)
    employees = eligibility.load_employees()
    job = eligibility.load_job(seed_catalog["jobs"]["flooring_tile"].id)
    result = scarcity.detect_scarce_skills(employees, [job])
    assert result == []


@pytest.mark.phase8
def test_tile_scarce_across_two_jobs(scarcity: ScarcityService, seed_catalog, db_session) -> None:
    eligibility = EligibilityService(db_session)
    employees = eligibility.load_employees()
    jobs = [
        eligibility.load_job(seed_catalog["jobs"]["demo_cleaning"].id),
        eligibility.load_job(seed_catalog["jobs"]["flooring_tile"].id),
    ]
    scarce = scarcity.detect_scarce_skills(employees, jobs)
    tile = next((s for s in scarce if s.skill_name == "Tile"), None)
    assert tile is not None
    assert tile.available_count == 1
    assert tile.demanded_count >= 1
    assert seed_catalog["employees"]["taylor_tile"].id in tile.employee_ids


@pytest.mark.phase8
def test_scarcity_warning_when_misassigned(scarcity: ScarcityService, seed_catalog, db_session) -> None:
    eligibility = EligibilityService(db_session)
    employees = eligibility.load_employees()
    jobs = [
        eligibility.load_job(seed_catalog["jobs"]["demo_cleaning"].id),
        eligibility.load_job(seed_catalog["jobs"]["flooring_tile"].id),
    ]
    taylor = eligibility.load_employees([seed_catalog["employees"]["taylor_tile"].id])[0]
    cleaning_job = jobs[0]
    warning = scarcity.manual_override_scarcity_warning(taylor, cleaning_job, employees, jobs)
    assert warning is not None
    assert "scarce" in warning.lower()


@pytest.mark.phase8
def test_no_warning_when_scarce_worker_on_correct_job(
    scarcity: ScarcityService, seed_catalog, db_session
) -> None:
    eligibility = EligibilityService(db_session)
    employees = eligibility.load_employees()
    jobs = [
        eligibility.load_job(seed_catalog["jobs"]["demo_cleaning"].id),
        eligibility.load_job(seed_catalog["jobs"]["flooring_tile"].id),
    ]
    taylor = eligibility.load_employees([seed_catalog["employees"]["taylor_tile"].id])[0]
    tile_job = jobs[1]
    warning = scarcity.manual_override_scarcity_warning(taylor, tile_job, employees, jobs)
    assert warning is None
