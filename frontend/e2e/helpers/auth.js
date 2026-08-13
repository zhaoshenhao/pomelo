import { request } from "@playwright/test";

export const API_BASE = process.env.E2E_API_BASE || "http://localhost:8080";

export const ADMIN_USERNAME = process.env.E2E_ADMIN_USERNAME || "admin";
export const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || "";

export async function apiLogin(username, password) {
  const ctx = await request.newContext({ baseURL: API_BASE });
  const resp = await ctx.post("/api/auth/login", { data: { username, password } });
  const body = await resp.json();
  await ctx.dispose();
  if (resp.status() !== 200 || !body.data?.access_token) {
    throw new Error(`login failed for ${username}: ${resp.status()}`);
  }
  return body.data;
}

export async function loginAs(page, username, password) {
  const data = await apiLogin(username, password);
  await page.addInitScript(
    ({ token }) => {
      localStorage.setItem("access_token", token);
      localStorage.setItem("refresh_token", token);
    },
    { token: data.access_token },
  );
  return data;
}

export async function loginAsAdmin(page) {
  return loginAs(page, ADMIN_USERNAME, ADMIN_PASSWORD);
}
