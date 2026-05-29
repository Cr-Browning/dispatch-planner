import { expect, test } from "@playwright/test";

const password = process.env.DISPATCHER_PASSWORD ?? "changeme";

test("login, solve dispatch, export csv", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible({
    timeout: 30_000,
  });

  await page.goto("/dispatch?date=2026-06-15");
  await expect(page.getByRole("heading", { name: "Daily dispatch planner" })).toBeVisible();

  await page.getByRole("button", { name: "Select all for this date" }).click();
  const jobCheckbox = page.locator('table.data-table tbody input[type="checkbox"]').first();
  await expect(jobCheckbox).toBeChecked({ timeout: 15_000 });

  await page.getByRole("button", { name: "Create & solve" }).click();
  await expect(page.getByRole("heading", { name: /Route review/i })).toBeVisible({
    timeout: 60_000,
  });

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: /download csv/i }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.csv$/i);
});
