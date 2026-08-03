<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-900 via-primary-800 to-accent-900">
    <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,_var(--tw-gradient-stops))] from-primary-500/10 via-transparent to-transparent"></div>

    <div class="relative w-full max-w-md mx-4">
      <div class="bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl shadow-2xl p-8">
        <div class="text-center mb-6">
          <div class="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-primary-400 to-accent-500 mb-3 shadow-lg shadow-accent-500/20">
            <span class="text-xl">&#x1F34A;</span>
          </div>
          <h1 class="text-2xl font-bold text-white">创建账户</h1>
          <p class="text-primary-200 text-sm mt-1">加入 Pomelo 学习平台</p>
        </div>

        <form @submit.prevent="handleRegister" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-primary-100 mb-1">用户名</label>
            <input
              v-model="form.username"
              type="text"
              required
              placeholder="请输入用户名"
              class="w-full px-4 py-2.5 rounded-xl bg-white/10 border border-white/20 text-white placeholder-white/40
                     focus:outline-none focus:ring-2 focus:ring-accent-400 focus:border-transparent transition"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-primary-100 mb-1">展示名 <span class="text-white/40 text-xs">(可选)</span></label>
            <input
              v-model="form.display_name"
              type="text"
              placeholder="如何称呼您"
              class="w-full px-4 py-2.5 rounded-xl bg-white/10 border border-white/20 text-white placeholder-white/40
                     focus:outline-none focus:ring-2 focus:ring-accent-400 focus:border-transparent transition"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-primary-100 mb-1">邮箱</label>
            <input
              v-model="form.email"
              type="email"
              required
              placeholder="your@email.com"
              class="w-full px-4 py-2.5 rounded-xl bg-white/10 border border-white/20 text-white placeholder-white/40
                     focus:outline-none focus:ring-2 focus:ring-accent-400 focus:border-transparent transition"
            />
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm font-medium text-primary-100 mb-1">手机</label>
              <input
                v-model="form.phone"
                type="text"
                required
                placeholder="手机号"
                class="w-full px-4 py-2.5 rounded-xl bg-white/10 border border-white/20 text-white placeholder-white/40
                       focus:outline-none focus:ring-2 focus:ring-accent-400 focus:border-transparent transition"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-primary-100 mb-1">部门 <span class="text-white/40 text-xs">(可选)</span></label>
              <select
                v-model="form.department_id"
                class="w-full px-4 py-2.5 rounded-xl bg-white/10 border border-white/20 text-white focus:outline-none focus:ring-2 focus:ring-accent-400 transition"
              >
                <option :value="null" class="text-gray-900">无</option>
                <option v-for="d in departments" :key="d.id" :value="d.id" class="text-gray-900">{{ d.name }}</option>
              </select>
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-primary-100 mb-1">密码</label>
            <input
              v-model="form.password"
              type="password"
              required
              placeholder="至少 6 位密码"
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
            <span v-if="!loading">注 册</span>
            <span v-else class="inline-flex items-center gap-2">
              <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
              注册中...
            </span>
          </button>
        </form>

        <div class="mt-6 pt-5 border-t border-white/10 text-center">
          <p class="text-sm text-primary-200">
            已有账户？
            <NuxtLink to="/login" class="text-accent-300 hover:text-accent-200 font-medium transition">立即登录</NuxtLink>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";

definePageMeta({ layout: false });
const router = useRouter();
const { $api } = useNuxtApp();
const form = ref({ username: "", display_name: "", email: "", phone: "", department_id: null, password: "" });
const departments = ref([]);
const error = ref("");
const loading = ref(false);

async function fetchDepartments() {
  try {
    const res = await $api.get("/departments");
    departments.value = res.data.data;
  } catch {}
}

async function handleRegister() {
  error.value = "";
  loading.value = true;
  try {
    const body = {
      username: form.value.username,
      display_name: form.value.display_name || form.value.username,
      email: form.value.email,
      phone: form.value.phone,
      department_id: form.value.department_id,
      password: form.value.password,
    };
    await $api.post("/auth/register", body);
    router.push("/login");
  } catch (e) {
    error.value = e.response?.data?.detail || "注册失败，请检查输入信息";
  } finally {
    loading.value = false;
  }
}

onMounted(() => { fetchDepartments(); });
</script>
