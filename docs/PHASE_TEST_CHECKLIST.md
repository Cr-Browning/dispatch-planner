# Phase Test Checklist

**Rule:** Each implementation phase is not complete until its tests are added and `pytest` passes. Do not defer tests to a late "testing phase."

Run before marking any phase done:

```bash
cd dispatch-planner/backend
pytest
```

## Phase gates

| Phase | Feature | Required test files | Status |
|------:|---------|---------------------|--------|
| 1 | Architecture | (none) | n/a |
| 2 | DB schema | `test_models.py` | done |
| 3 | Scaffold + auth | `test_health.py`, `test_auth.py`, `test_security.py` | done |
| 4 | CRUD | `test_employee_skills.py`, `test_employee_locations.py`, `test_api_employees.py`, `test_api_skills.py`, `test_api_jobs.py` | done |
| 5 | Seed data | `test_seed_data.py` | done |
| 6 | Routing interface | `test_routing_provider_mock.py`, `test_route_matrix_cache.py` | done |
| 7 | Google routing | `test_routing_google.py`, `test_api_routing_config.py` | done |
| 8 | Eligibility + scarcity | `test_eligibility.py`, `test_scarcity.py` | done |
| 9 | Assignment solver | `test_assignment_solver.py` | done |
| 10 | Route solver | `test_route_solver.py` | done |
| 11 | Manual override | `test_manual_overrides.py` | done |
| 12 | CSV export | `test_export_csv.py` | done |
| 13 | Frontend | `frontend/src/__tests__/*`, `test_api_settings.py` | done |
| 14 | Map preview | `frontend/src/__tests__/routeMap.test.ts`, `test_dispatch_plan.py` | done |
| 15 | Final tests + docs | `test_api_dispatch.py`, `test_api_backups.py`, README, `.env.example` | done |
| — | Dispatch API (consolidated) | `test_api_dispatch.py` | done |
| — | Settings / backups | `test_api_settings.py`, `test_api_backups.py` | done |

## Shared fixtures (`conftest.py`)

| Fixture | Used from phase |
|---------|-----------------|
| `db_session` | 2+ |
| `client`, `auth_headers` | 3+ |
| `skill_factory`, `employee_factory`, `job_factory` | 4+ |
| `seed_catalog` | 5+ |
| `mock_routing_provider` | 6+ |
| `tmp_export_dir`, `tmp_backup_dir` | 12+ |

## Agent reporting template

```text
Tests added:
- ...

Behavior covered:
- ...

Commands run:
- pytest

Result:
- pass/fail

Known untested areas:
- ...
```

Update the **Status** column in this file when completing each phase.
