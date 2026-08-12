export default defineNuxtRouteMiddleware(async () => {
  if (!process.client) return;
  const authStore = useAuthStore();
  await authStore.init();
  if (!authStore.isAuthenticated) {
    return navigateTo("/login");
  }
  if (!authStore.isTeacherOrAdmin) {
    return navigateTo("/");
  }
});
