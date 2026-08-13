import { test, expect } from "@playwright/test";
import { ADMIN_USERNAME, ADMIN_PASSWORD } from "./helpers/auth";

test("login page renders and logs in via UI", async ({ page }) => {
  await page.goto("/login");
  await expect(page.locator("h1").first()).toContainText("Pomelo");
  // Allow client-side hydration to complete (submit handler attachment).
  await page.waitForTimeout(1500);

  await page.locator('input[type="text"]').fill(ADMIN_USERNAME);
  await page.locator('input[type="password"]').fill(ADMIN_PASSWORD);
  await page.locator('input[type="password"]').press("Enter");

  await expect(page).not.toHaveURL(/\/login/, { timeout: 15_000 });
});

test("unauthenticated visit redirects to login", async ({ page }) => {
  await page.goto("/admin/question-banks");
  await expect(page).toHaveURL(/\/login/);
});
