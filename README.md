# Employee Dispatch Route Optimizer

Local-first internal web app for daily job assignment and pickup route optimization.

**Reviewers:** follow [First-time setup](#first-time-setup) below. Default sign-in after `cp .env.example .env` is password **`changeme`**.  
**Maintainers:** see [SUBMISSION.md](SUBMISSION.md) before packaging or pushing to GitHub.

## Status

All planned phases (1–15) are implemented: database, API, solvers, CSV export, React UI, map preview, and documentation.

| Area | Stack |
|------|--------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy, SQLite |
| Frontend | React 19, Vite, TypeScript, Leaflet (OpenStreetMap) |
| Routing | Pluggable provider (`mock` default, `google` optional) |
| Auth | Single dispatcher password → JWT (no per-employee login) |

See [docs/PHASE_TEST_CHECKLIST.md](docs/PHASE_TEST_CHECKLIST.md), [docs/MIGRATION_STRATEGY.md](docs/MIGRATION_STRATEGY.md), and [docs/SEED_DATA_STRATEGY.md](docs/SEED_DATA_STRATEGY.md).

## Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- No Docker required
- Google Maps API key **optional** (mock routing works offline)

## First-time setup

### 1. Backend

```bash
cd dispatch-planner/backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env`:

- `APP_SECRET_KEY` — any long random string for JWT signing: openssl rand -hex 32p
- `DISPATCHER_PASSWORD` — password used to sign in to the UI and API

### 2. Database and seed data

From `dispatch-planner/backend` with the venv active:

```bash
python -m app.seed
```

Idempotent: safe to re-run. Loads 10 employees (3 drivers), 14 skills, 4 jobs, optimization profiles, and default settings.

### 3. Frontend

```bash
cd dispatch-planner/frontend
npm install
```

## Local run (daily)

Use two terminals.

**Terminal A — API**

```bash
cd dispatch-planner/backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API docs: http://localhost:8000/docs  
- Health: http://localhost:8000/health  

**Terminal B — UI**

```bash
cd dispatch-planner/frontend
npm run dev
```

- App: http://localhost:5173 (Vite proxies `/api` to port 8000)  
- Sign in with `DISPATCHER_PASSWORD` from `backend/.env`

### Typical dispatcher workflow

1. **Dashboard** — today's job count, dispatch runs, and jobs missing roles.
2. **Dispatch planner** — date defaults to today; **Select all for this date**; add jobs with **Add job** (arrival pre-filled for that date).
3. **Create & solve** — review assignments on route review; or **Create, solve & download CSV** for a one-step export.
4. **Route review** — map, ETAs, **Re-solve** a single job, manual overrides → **Recalculate all routes** before CSV if routes are stale.
5. **Copy last run's jobs** — copies job IDs and warns when arrivals are not on the selected date.
6. New jobs **geocode on save** when coordinates are omitted (mock or Google provider).

Dates are shown as **MM-DD-YYYY** in the UI and CSV exports. APIs and date pickers still use `YYYY-MM-DD` internally.

### API-only smoke test

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"password":"changeme"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Create + solve (replace job IDs from GET /jobs after seeding)
curl -s -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"run_date":"2026-06-15","name":"CLI test","job_ids":[1,2]}' \
  http://localhost:8000/dispatch-runs
```

## Tests

```bash
# Backend (from dispatch-planner/backend, venv active)
pytest
pytest -m phase15          # dispatch API + quality-bar flow
pytest -m integration        # Google routing (skipped without API key)

# Frontend
cd dispatch-planner/frontend
npm test
npm run build

# End-to-end (Playwright; seeds data/e2e-smoke.db, starts API :8001 + UI :5174)
npx playwright install chromium
npm run test:e2e
```

Fixtures: `app/tests/conftest.py`, factories in `app/tests/factories.py`.

## Project layout

```text
dispatch-planner/
  backend/app/       # FastAPI application
  frontend/          # React UI
  data/              # SQLite (gitignored)
  backups/           # Reserved for backup files
  exports/           # Generated CSV schedules
  docs/              # Schema, migration, phase checklist
```

## Configuration reference

| Variable | Purpose |
|----------|---------|
| `APP_SECRET_KEY` | JWT signing |
| `DISPATCHER_PASSWORD` | Login password |
| `DATABASE_URL` | SQLite path (relative to `dispatch-planner/`) |
| `EXPORT_DIR` | CSV output directory |
| `BACKUP_DIR` | Backup storage (`POST/GET /backups`, restore from Settings) |
| `ROUTING_PROVIDER` | `mock` or `google` |
| `GOOGLE_MAPS_API_KEY` | Required when `ROUTING_PROVIDER=google` |
| `BACKUP_ON_STARTUP` | `true` to copy SQLite to `BACKUP_DIR` when API starts |

Restart the API after changing `.env`.

## Google routing (optional)

Default is **mock** routing (deterministic, no network). For live drive times and distances:

```bash
GOOGLE_MAPS_API_KEY=your-key-here
ROUTING_PROVIDER=google
```

Optional live tests:

```bash
GOOGLE_MAPS_API_KEY=your-key pytest -m integration
```

The **browser never loads a Google Maps API key**; map preview uses OpenStreetMap tiles. Google appears only as external navigation links and on the server when configured.

## Features by area

- **Assignment** — skill eligibility, scarcity awareness, substitution, headcount (`POST /dispatch-runs/{id}/solve`).
- **Routes** — pickup order, capacity, ETAs, lateness warnings, Google Maps URLs (`GET .../plan`).
- **Overrides** — move assignment, reorder pickups (`POST .../manual-override`, `POST .../recalculate`).
- **Export** — schedule CSV: date, job, client, job address, arrival time, driver, driver phone, employee name, Google Maps link, notes (`POST .../export-csv`).
- **Map** — read-only pins and route lines on route review (Leaflet).

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|----------------|-----|
| UI login fails | Wrong password or API down | Match `DISPATCHER_PASSWORD` in `backend/.env`; confirm API on :8000 |
| `401` on API calls | Missing/expired JWT | Log in again; token stored in browser `localStorage` |
| Empty solve / no routes | Jobs lack coordinates or ineligible pool | Re-run seed; check employee skills and job requirements in UI |
| `sqlite3.OperationalError` / DB locked | Multiple writers | Use one API process; avoid editing `data/dispatch.db` while server runs |
| Paths not found for DB/exports | Wrong working directory | Paths in `.env` are relative to `dispatch-planner/`, not `backend/` |
| Frontend cannot reach API | Proxy / CORS | Run Vite dev server (`npm run dev`); production build needs API URL config |
| Google routing errors | Key or billing | Verify key, enable Routes/Distance Matrix APIs; fall back to `ROUTING_PROVIDER=mock` |
| Map shows “No route coordinates” | Unsolved run or missing lat/lng | Solve the run first; ensure seed locations have coordinates |
| Driver phone empty in CSV | No phone on employee | Add **Phone** on the employee edit form (drivers especially) |
| Tests fail on import | Stale venv | `pip install -r requirements.txt` in `backend/.venv` |

Reset local data: stop the API, delete `data/dispatch.db` (and `-wal`/`-shm` if present), run `python -m app.seed` again.

## Known limitations

- **Single dispatcher account** — one shared password, not per-user RBAC.
- **SQLite** — single-writer; not aimed at multi-tenant cloud scale without migration.
- **Mock routing** — straight-line / heuristic times unless Google provider is enabled.
- **Assignment heuristic** — not a guaranteed global optimum; reasoning and warnings explain tradeoffs.
- **Backups** — `POST /backups` and `GET /backups`; optional `BACKUP_ON_STARTUP` in `.env`.
- **No mobile app, payroll, notifications, or QuickBooks** — out of scope per product spec.
- **Map lines** — geometry from routing provider or stop-to-stop fallback; not turn-by-turn in-app navigation.
- **Substitution rules** — limited to configured skill graph; edge cases may need manual override.

## Extension roadmap

| Priority | Idea |
|----------|------|
| Near | Scheduled automatic backups (manual + startup backup already supported) |
| Near | Postgres option behind `DATABASE_URL` |
| Medium | Multi-dispatcher users and audit log for overrides |
| Medium | Re-optimize single job without full re-solve |
| Medium | Historical run comparison / duplicate day planner |
| Later | Live traffic refresh and push ETA updates |
| Later | Driver mobile view (read-only routes, no optimization in browser) |
| Later | Webhook or email when a run has lateness warnings |

## License / usage

Internal operations tool. Do not commit `backend/.env` or API keys (see `.gitignore`).
