import axios from "axios";

const apiClient = axios.create({
  baseURL: "http://localhost:8080/api",
  timeout: 300000,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  if (process.client) {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const { $logger } = useNuxtApp();
    const status = error.response?.status || 0;
    const url = error.config?.url || "";
    const method = error.config?.method?.toUpperCase() || "";

    if (status >= 500) {
      $logger.error("axios", `API error: ${method} ${url}`, { status, data: error.response?.data });
    } else if (status >= 400) {
      $logger.warn("axios", `API client error: ${method} ${url}`, { status });
    } else if (status === 0) {
      $logger.error("axios", `Network error: ${method} ${url}`, { message: error.message });
    }

    if (status === 401 && process.client) {
      const authStore = useAuthStore();
      authStore.logout();
    }
    return Promise.reject(error);
  },
);

export default defineNuxtPlugin(() => {
  return {
    provide: {
      api: apiClient,
    },
  };
});
