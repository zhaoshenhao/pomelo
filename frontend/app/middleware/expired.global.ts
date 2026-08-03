import { isTokenExpired } from "@/utils/auth";

export default defineNuxtRouteMiddleware(() => {
  if (!process.client) return;
  const authStore = useAuthStore();
  if (!authStore.accessToken) return;
  if (isTokenExpired(authStore.accessToken)) {
    authStore.logout();
  }
});
