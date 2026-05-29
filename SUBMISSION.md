# Submission checklist (maintainer)

Use this before sending the project to the client or reviewer.

## Do not ship

- `backend/.env` (secrets) — only `backend/.env.example`
- `backend/.venv/`, `frontend/node_modules/`
- `data/*.db`, `data/*.db-wal`, `data/*.db-shm`
- `backups/*` (except `.gitkeep`), `exports/*` (except `.gitkeep`)
- `frontend/test-results/`, `frontend/playwright-report/`

## Recipient setup (5 minutes)

1. `cd dispatch-planner/backend` → venv, `pip install -r requirements.txt`, `cp .env.example .env`
2. Change `APP_SECRET_KEY` and `DISPATCHER_PASSWORD` in `.env`
3. `python -m app.seed`
4. `cd ../frontend` → `npm ci`
5. Run API (`uvicorn`) and UI (`npm run dev`) — see [README.md](README.md)

Default login password after copying `.env.example`: **`changeme`**

## Verify before send

```bash
# Backend
cd backend && source .venv/bin/activate && pytest -q

# Frontend
cd ../frontend && npm test && npm run build

# E2E (optional, ~2 min)
npx playwright install chromium && npm run test:e2e
```

## Demo data

Seed creates 4 jobs on **2026-06-15**. Use the dispatch planner with that date (or Dashboard → Plan today if you re-seed with current dates).

## GitHub

Initialize git at **`dispatch-planner/`** (recommended) or at the parent `routing-assignment/` folder. If using only `dispatch-planner/` as the repo root, use `dispatch-planner/.github/workflows/e2e.yml` and remove the parent workflow to avoid duplicate CI runs.
