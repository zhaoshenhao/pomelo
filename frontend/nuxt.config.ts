import tailwindcss from "@tailwindcss/vite";

export default defineNuxtConfig({
  compatibilityDate: "2025-07-15",
  devtools: { enabled: true },
  modules: ["@pinia/nuxt"],
  css: ["~/assets/css/main.css"],
  vite: {
    plugins: [tailwindcss()],
  },
  runtimeConfig: {
    public: {
      apiBase: "",
      examDebug: "false",
      examEstSingle: 60,
      examEstMultiple: 80,
      examEstTrueFalse: 45,
      examEstFill: 80,
      examEstMatch: 120,
    },
  },
  devServer: {
    port: 3000,
  },
  app: {
    head: {
      script: [{ src: "/config.js" }],
    },
  },
})
