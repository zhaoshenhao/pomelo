<template>
  <div class="max-w-2xl mx-auto">
    <div class="mb-6">
      <h2 class="text-xl font-bold text-gray-900">个人设置</h2>
      <p class="text-sm text-gray-500 mt-1">修改个人信息和密码</p>
    </div>

    <div class="space-y-6">
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 class="text-base font-semibold text-gray-900 mb-4">基本信息</h3>
        <form @submit.prevent="handleProfileUpdate" class="space-y-3 max-w-sm">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">展示名</label>
            <input v-model="profile.display_name" :placeholder="authStore.user?.username" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">用户名</label>
            <input v-model="profile.username" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
            <input v-model="profile.email" type="email" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" />
          </div>
          <button type="submit" :disabled="profileLoading" class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50">{{ profileLoading ? '保存中...' : '保存' }}</button>
        </form>
      </div>

      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 class="text-base font-semibold text-gray-900 mb-4">修改密码</h3>
        <form @submit.prevent="handlePasswordChange" class="space-y-3 max-w-sm">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">旧密码</label>
            <input v-model="passwordForm.old_password" type="password" required class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">新密码</label>
            <input v-model="passwordForm.new_password" type="password" required minlength="6" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">确认新密码</label>
            <input v-model="passwordForm.confirm_password" type="password" required class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" />
          </div>
          <button type="submit" :disabled="pwdLoading" class="px-4 py-2 bg-accent-600 text-white text-sm rounded-lg hover:bg-accent-700 disabled:opacity-50">{{ pwdLoading ? '修改中...' : '修改密码' }}</button>
        </form>
      </div>
    </div>

    <div v-if="message" class="mt-4 px-4 py-3 rounded-xl text-sm" :class="msgClass">{{ message }}</div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";

definePageMeta({ middleware: "auth" });

const authStore = useAuthStore();
const { $api } = useNuxtApp();

const profile = ref({ username: "", display_name: "", email: "" });
const profileLoading = ref(false);
const passwordForm = ref({ old_password: "", new_password: "", confirm_password: "" });
const pwdLoading = ref(false);
const message = ref("");
const msgType = ref("success");

const msgClass = computed(() => msgType.value === "success" ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200");

function initProfile() {
  if (authStore.user) {
    profile.value = {
      username: authStore.user.username,
      display_name: authStore.user.display_name || "",
      email: authStore.user.email,
    };
  }
}

async function handleProfileUpdate() {
  profileLoading.value = true;
  try {
    const body = {};
    if (profile.value.username !== authStore.user?.username) body.username = profile.value.username;
    if (profile.value.display_name !== (authStore.user?.display_name || "")) body.display_name = profile.value.display_name || null;
    if (profile.value.email !== authStore.user?.email) body.email = profile.value.email;
    if (Object.keys(body).length === 0) { showMessage("没有修改", "error"); return; }
    const res = await $api.patch("/auth/profile", body);
    authStore.setUser(res.data.data);
    showMessage("保存成功", "success");
  } catch (e) {
    showMessage(e.response?.data?.detail || "保存失败", "error");
  } finally {
    profileLoading.value = false;
  }
}

async function handlePasswordChange() {
  if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
    showMessage("两次密码不一致", "error");
    return;
  }
  if (passwordForm.value.new_password.length < 6) {
    showMessage("新密码至少 6 位", "error");
    return;
  }
  pwdLoading.value = true;
  try {
    await $api.post("/auth/change-password", {
      old_password: passwordForm.value.old_password,
      new_password: passwordForm.value.new_password,
    });
    passwordForm.value = { old_password: "", new_password: "", confirm_password: "" };
    showMessage("密码修改成功", "success");
  } catch (e) {
    showMessage(e.response?.data?.detail || "密码修改失败", "error");
  } finally {
    pwdLoading.value = false;
  }
}

function showMessage(msg, type) {
  message.value = msg;
  msgType.value = type;
  setTimeout(() => { message.value = ""; }, 3000);
}

initProfile();
</script>
