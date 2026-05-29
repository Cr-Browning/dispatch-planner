# Migration Strategy

## MVP approach

The application uses **SQLAlchemy `Base.metadata.create_all()`** on application startup (see `app/core/database.py`). This keeps local setup simple and avoids Alembic boilerplate for the initial build.

A schema version stamp is stored in `app_settings` under key `schema_version` (currently `1`).

## When to adopt Alembic

Switch to Alembic before:

- Production data must be preserved across schema changes
- Multiple environments need reproducible upgrades
- Team members rely on migration history for rollbacks

## Indexes and constraints (Phase 2)

| Table | Index / constraint | Purpose |
|-------|-------------------|---------|
| `employee_skills` | `uq_employee_skill`, `ck_proficiency_range` | One row per skill; proficiency 1–5 |
| `job_required_skills` | `ck_job_min_proficiency` | Minimum proficiency 1–5 |
| `dispatch_run_jobs` | `uq_dispatch_run_job` | Job appears once per run |
| `dispatch_run_employee_locations` | `uq_dispatch_run_employee` | One active location per employee per run |
| `dispatch_assignments` | `uq_dispatch_run_employee_assignment` | One job per employee per run |
| `route_matrix_cache` | `ix_route_matrix_lookup` | Fast cache lookups by O/D + mode + tolls |
| Foreign keys | `ON DELETE CASCADE` where child rows are owned by parent | Consistent cleanup |

## SQLite notes

- Enable WAL mode in `database.py` for better concurrent read performance on LAN.
- Use `check_same_thread=False` only where required by the test harness.
- Back up via `BackupService` (file copy) before destructive schema experiments.

## Upgrade path from create_all

1. Initialize Alembic in `backend/`.
2. Generate initial revision from current models.
3. Set `schema_version` in DB to match revision id.
4. Disable `create_all` in production; run `alembic upgrade head` instead.
