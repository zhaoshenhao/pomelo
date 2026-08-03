import { defineStore } from "pinia";

interface User {
  id: number;
  username: string;
  display_name: string | null;
  email: string;
  phone: string;
  department_id: number | null;
  department_name: string | null;
  role: "admin" | "teacher" | "student";
  is_active: boolean;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
}

export const useAuthStore = defineStore("auth", {
  state: (): AuthState => ({
    user: null,
    accessToken: null,
    refreshToken: null,
  }),

  getters: {
    isAuthenticated: (state) => !!state.accessToken,
    isAdmin: (state) => state.user?.role === "admin",
    isTeacher: (state) => state.user?.role === "teacher",
    isTeacherOrAdmin: (state) =>
      state.user?.role === "teacher" || state.user?.role === "admin",
    displayName: (state) => state.user?.display_name || state.user?.username || "",
  },

  actions: {
    setTokens(accessToken: string, refreshToken: string) {
      this.accessToken = accessToken;
      this.refreshToken = refreshToken;
      if (process.client) {
        localStorage.setItem("access_token", accessToken);
        localStorage.setItem("refresh_token", refreshToken);
      }
    },

    setUser(user: User) {
      this.user = user;
    },

    async login(username: string, password: string) {
      const { $api } = useNuxtApp();
      const response = await $api.post("/auth/login", { username, password });
      this.setTokens(response.data.data.access_token, response.data.data.refresh_token);
      this.setUser(response.data.data.user);
    },

    async fetchUser() {
      const { $api } = useNuxtApp();
      const response = await $api.get("/auth/me");
      this.setUser(response.data.data);
    },

    logout() {
      this.user = null;
      this.accessToken = null;
      this.refreshToken = null;
      if (process.client) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
      }
      navigateTo("/login");
    },

    async init() {
      if (process.client) {
        const token = localStorage.getItem("access_token");
        if (token) {
          this.accessToken = token;
          this.refreshToken = localStorage.getItem("refresh_token");
          try {
            await this.fetchUser();
          } catch {
            this.logout();
          }
        }
      }
    },
  },
});
