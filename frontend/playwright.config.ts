/// <reference types="node" />
import path from "node:path";
import { defineConfig } from "@playwright/test";

const apiPort = process.env.E2E_API_PORT ?? "8001";
const uiPort = process.env.E2E_UI_PORT ?? "5174";
const dbPath = path.resolve(process.cwd(), "..", "data", "e2e-smoke.db");
const dbUrl = `sqlite:///${dbPath}`;
const dispatcherPassword = process.env.DISPATCHER_PASSWORD ?? "changeme";
const apiEnv = `DATABASE_URL=${dbUrl} DISPATCHER_PASSWORD=${dispatcherPassword} BACKUP_ON_STARTUP=false`;

export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  expect: { timeout: 15_000 },
  use: {
    baseURL: `http://127.0.0.1:${uiPort}`,
    trace: "on-first-retry",
  },
  webServer: [
    {
      command: `cd ../backend && rm -f ../data/e2e-smoke.db ../data/e2e-smoke.db-wal ../data/e2e-smoke.db-shm && ${apiEnv} .venv/bin/python -m app.seed && ${apiEnv} .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port ${apiPort}`,
      url: `http://127.0.0.1:${apiPort}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${uiPort}`,
      url: `http://127.0.0.1:${uiPort}`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        E2E_API_PROXY: `http://127.0.0.1:${apiPort}`,
      },
    },
  ],
});
