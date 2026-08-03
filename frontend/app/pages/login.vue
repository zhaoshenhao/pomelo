<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-900 via-primary-800 to-accent-900">
    <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-accent-500/10 via-transparent to-transparent"></div>

    <div class="relative w-full max-w-md mx-4">
      <div class="bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl shadow-2xl p-8">
        <div class="text-center mb-8">
          <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-400 to-accent-500 mb-4 shadow-lg shadow-accent-500/20">
            <span class="text-3xl">&#x1F34A;</span>
          </div>
          <h1 class="text-3xl font-bold text-white tracking-tight">Pomelo</h1>
          <p class="text-primary-200 text-sm mt-1">基于文档的学习平台</p>
        </div>

        <form @submit.prevent="handleLogin" class="space-y-5">
          <div>
            <label class="block text-sm font-medium text-primary-100 mb-1.5">用户名</label>
            <input
              v-model="username"
              type="text"
              required
              placeholder="请输入用户名"
              class="w-full px-4 py-2.5 rounded-xl bg-white/10 border border-white/20 text-white placeholder-white/40
                     focus:outline-none focus:ring-2 focus:ring-accent-400 focus:border-transparent transition"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-primary-100 mb-1.5">密码</label>
            <input
              v-model="password"
              type="password"
              required
              placeholder="请输入密码"
              class="w-full px-4 py-2.5 rounded-xl bg-white/10 border border-white/20 text-white placeholder-white/40
                     focus:outline-none focus:ring-2 focus:ring-accent-400 focus:border-transparent transition"
            />
          </div>

          <div v-if="error" class="px-4 py-2.5 rounded-xl bg-red-500/20 border border-red-400/30 text-red-200 text-sm">
            {{ error }}
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full py-2.5 rounded-xl font-semibold text-white
                   bg-gradient-to-r from-primary-500 to-accent-500
                   hover:from-primary-400 hover:to-accent-400
                   shadow-lg shadow-accent-500/25
                   disabled:opacity-50 disabled:cursor-not-allowed
                   transition-all duration-200"
          >
            <span v-if="!loading">登 录</span>
            <span v-else class="inline-flex items-center gap-2">
              <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
              登录中...
            </span>
          </button>
        </form>

        <div class="mt-6 pt-5 border-t border-white/10 text-center">
          <p class="text-sm text-primary-200">
            没有账户？
            <NuxtLink to="/register" class="text-accent-300 hover:text-accent-200 font-medium transition">立即注册</NuxtLink>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";

definePageMeta({ layout: false });
const authStore = useAuthStore();
const router = useRouter();
const username = ref("");
const password = ref("");
const error = ref("");
const loading = ref(false);

async function handleLogin() {
  error.value = "";
  loading.value = true;
  try {
    await authStore.login(username.value, password.value);
    router.push("/");
  } catch (e) {
    error.value = e.response?.data?.detail || "登录失败，请检查用户名和密码";
  } finally {
    loading.value = false;
  }
}

if (process.client) {
  await authStore.init();
  if (authStore.isAuthenticated) {
    router.push("/");
  }
}
</script>
