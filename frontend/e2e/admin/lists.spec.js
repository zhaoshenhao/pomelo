import { test, expect } from "@playwright/test";
import { loginAsAdmin } from "../helpers/auth";

test.beforeEach(async ({ page }) => {
  await loginAsAdmin(page);
});

test("question banks list renders", async ({ page }) => {
  await page.goto("/admin/question-banks");
  await expect(page.locator("h2").first()).toContainText("题库");
  await expect(page.locator("table, .overflow-x-auto").first()).toBeVisible();
});

test("study materials list renders", async ({ page }) => {
  await page.goto("/admin/study-materials");
  await expect(page.locator("h2").first()).toContainText("学习资料");
  await expect(page.locator("table").first()).toBeVisible();
});

test("videos list renders", async ({ page }) => {
  await page.goto("/admin/videos");
  await expect(page.locator("h2").first()).toContainText("视频");
  await expect(page.locator("table").first()).toBeVisible();
});

test("exams list renders", async ({ page }) => {
  await page.goto("/admin/exams");
  await expect(page.locator("h2").first()).toContainText("试卷");
  await expect(page.locator("table, .overflow-x-auto").first()).toBeVisible();
});
