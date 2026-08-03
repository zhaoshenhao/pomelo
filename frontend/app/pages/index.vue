<template>
  <div>
    <div class="mb-6">
      <h2 class="text-xl font-bold text-gray-900">工作台</h2>
      <p class="text-sm text-gray-500 mt-1">欢迎回来，{{ authStore.user?.username }}</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
      <div class="p-5 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 text-white shadow-lg shadow-primary-500/20">
        <div class="text-2xl mb-2">&#x1F4C4;</div>
        <h3 class="font-semibold text-white/90 mb-1">文档管理</h3>
        <p class="text-sm text-white/70">上传和管理学习文档资料</p>
      </div>
      <div class="p-5 rounded-xl bg-gradient-to-br from-accent-500 to-accent-600 text-white shadow-lg shadow-accent-500/20">
        <div class="text-2xl mb-2">&#x1F3AF;</div>
        <h3 class="font-semibold text-white/90 mb-1">学习任务</h3>
        <p class="text-sm text-white/70">根据课程安排完成学习任务</p>
      </div>
      <div class="p-5 rounded-xl bg-gradient-to-br from-primary-400 to-accent-500 text-white shadow-lg shadow-accent-500/20">
        <div class="text-2xl mb-2">&#x1F3C6;</div>
        <h3 class="font-semibold text-white/90 mb-1">结业证书</h3>
        <p class="text-sm text-white/70">通过测试获取结业证书</p>
      </div>
    </div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 class="text-lg font-semibold text-gray-900 mb-3">快速开始</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600">
        <div v-if="authStore.isAdmin" class="flex items-start gap-3 p-3 rounded-lg bg-primary-50">
          <span class="text-lg">&#x1F465;</span>
          <div>
            <p class="font-medium text-gray-800">管理用户</p>
            <NuxtLink to="/admin/users" class="text-primary-600 hover:underline">前往用户管理</NuxtLink>
          </div>
        </div>
        <div v-if="authStore.isTeacherOrAdmin" class="flex items-start gap-3 p-3 rounded-lg bg-accent-50">
          <span class="text-lg">&#x1F4DA;</span>
          <div>
            <p class="font-medium text-gray-800">管理文档库</p>
            <p class="text-xs text-gray-400 mt-0.5">功能开发中</p>
          </div>
        </div>
        <div class="flex items-start gap-3 p-3 rounded-lg bg-gray-50">
          <span class="text-lg">&#x1F4D6;</span>
          <div>
            <p class="font-medium text-gray-800">我的课程</p>
            <p class="text-xs text-gray-400 mt-0.5">功能开发中</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
definePageMeta({ middleware: "auth" });
const authStore = useAuthStore();
</script>
