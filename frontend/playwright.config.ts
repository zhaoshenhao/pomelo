import { defineConfig } from "@playwright/test";

// E2E runs against an already-running environment.
//   Local:      pnpm dev (frontend:3000) + uvicorn (backend:8080)
//   mb-test:    set E2E_BASE_URL / E2E_API_BASE below
const baseURL = process.env.E2E_BASE_URL || "http://localhost:3000";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
