"""Verify shared test fixtures stay valid across phases."""

import pytest

from app.seed.seed_data import SEED_EMPLOYEE_COUNT, SEED_JOB_COUNT


@pytest.mark.phase4
def test_seed_catalog_fixture_keys(seed_catalog: dict) -> None:
    assert len(seed_catalog["skills"]) >= 14
    assert len(seed_catalog["employees"]) == SEED_EMPLOYEE_COUNT
    assert len(seed_catalog["jobs"]) == SEED_JOB_COUNT
    assert "alex_driver" in seed_catalog["employees"]
    assert "taylor_tile" in seed_catalog["employees"]
    assert "demo_cleaning" in seed_catalog["jobs"]
    assert "riley_van" in seed_catalog["employees"]
    assert "mitigation_large" in seed_catalog["jobs"]
    assert "fewest_vehicles" in seed_catalog["profiles"]
