import { test, expect } from "@playwright/test";
import { loginAsAdmin } from "../helpers/auth";

// Smoke test that the student-facing course list loads with an authenticated session.
test("student dashboard and courses render", async ({ page }) => {
  await loginAsAdmin(page);
  await page.goto("/");
  await expect(page.locator("main, .flex-1").first()).toBeVisible();
});

test("student training page renders", async ({ page }) => {
  await loginAsAdmin(page);
  await page.goto("/student/training");
  await expect(page.locator("h2").first()).toBeVisible();
});

test("student videos page renders", async ({ page }) => {
  await loginAsAdmin(page);
  await page.goto("/student/videos");
  await expect(page.locator("h2").first()).toBeVisible();
});
