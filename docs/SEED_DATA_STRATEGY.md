# Seed Data Strategy

## Purpose

Seed data supports local development, manual UI testing, and automated tests without calling Google Maps APIs.

## Script location

`backend/app/seed/seed_data.py` (Phase 5 — implemented).

## Idempotency

The seed script should be **idempotent**:

1. Look up entities by stable natural keys (`Skill.name`, employee `display_name`, job `job_name`).
2. Insert only if missing; update coordinates/flags if fixtures change.
3. Safe to run after `create_all` on an empty or partially seeded database.

## Fixture contents (from product spec)

| Entity | Count | Notes |
|--------|------:|-------|
| Employees | 6 | 2 drivers, 4 workers |
| Skills | 14 | Demo, Drywall, Framing, … General labor |
| Jobs | 2 | Demo/Cleaning + Flooring/Tile |
| Locations | 6+ | One primary per employee; fake local addresses |
| Scarce skill | Tile @ 5 | Only Taylor Tile |
| Substitution | Job 1 | Contents → Cleaning |
| Vehicle capacities | 4 and 3 | Alex (4), Morgan (3) |

## Optimization profiles

Seed six `optimization_profiles` rows matching MVP profile names, with one `is_default=true` (`fewest_vehicles` objective chain).

## App settings

On first run, initialize:

- `schema_version`: `"1"`
- `dispatcher_password_hash`: bcrypt hash of `DISPATCHER_PASSWORD` env or default
- `export_include_addresses`: `false`

## Test usage

- `conftest.py` uses in-memory SQLite and `create_all` per test session or function.
- Optional `seed_database(session)` fixture for integration-style tests.
- Tests must not depend on Google APIs.

## Running seed (Phase 5+)

```bash
cd dispatch-planner/backend
python -m app.seed
```
