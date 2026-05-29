# Database Schema (Phase 2)

ORM definitions live in `backend/app/models/`. All tables use integer primary keys unless noted.

## Core entities

| Table | Purpose |
|-------|---------|
| `employees` | Worker/driver records with capacity and flags |
| `employee_locations` | Home, hotel, shop, etc. with optional lat/lng |
| `skills` | Skill catalog (Demo, Tile, …) |
| `employee_skills` | Proficiency 1–5 per employee/skill |
| `jobs` | Job templates with arrival time and headcount |
| `job_required_skills` | Required/preferred skills and quantities |
| `job_manual_substitutions` | Per-job allowed skill swaps |
| `job_included_employees` / `job_excluded_employees` | Must-include / exclude lists |

## Dispatch entities

| Table | Purpose |
|-------|---------|
| `dispatch_runs` | One daily planning session |
| `dispatch_run_jobs` | Jobs included in a run |
| `dispatch_run_employee_locations` | Active pickup location per employee per run |
| `dispatch_assignments` | Employee → job assignment (one job per employee per run) |
| `dispatch_vehicle_routes` | Driver vehicle route per job |
| `dispatch_route_stops` | Ordered pickup and job-site stops |

## Supporting tables

| Table | Purpose |
|-------|---------|
| `route_matrix_cache` | Cached travel times/distances |
| `optimization_profiles` | Objective ordering for solves |
| `export_records` | CSV export audit trail |
| `app_settings` | Key/value config (password hash, schema version, …) |
| `backup_records` | Database backup metadata |

## Key constraints

- `employee_skills`: unique `(employee_id, skill_id)`; proficiency 1–5
- `dispatch_assignments`: unique `(dispatch_run_id, employee_id)`
- `dispatch_run_employee_locations`: unique `(dispatch_run_id, employee_id)`
- `dispatch_run_jobs`: unique `(dispatch_run_id, job_id)`

See [MIGRATION_STRATEGY.md](MIGRATION_STRATEGY.md) for indexes and migration approach.
