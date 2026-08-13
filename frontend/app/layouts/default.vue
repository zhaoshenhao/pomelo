<template>
  <div class="h-screen bg-gray-50 flex">
    <aside
      class="w-64 bg-gradient-to-b from-primary-900 to-primary-950 text-white flex flex-col shrink-0"
      :class="{ 'hidden md:flex': !mobileOpen, 'fixed inset-y-0 left-0 z-50 flex': mobileOpen }"
    >
      <div class="p-5 border-b border-white/10">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-lg bg-gradient-to-br from-primary-400 to-accent-500 flex items-center justify-center shadow-md">
            <span class="text-white text-lg">&#x1F34A;</span>
          </div>
          <div>
            <h1 class="text-lg font-bold tracking-tight">Pomelo</h1>
            <p class="text-xs text-primary-300"><ClientOnly>{{ userRoleLabel }}</ClientOnly></p>
          </div>
        </div>
      </div>

      <nav class="flex-1 p-3 space-y-1 overflow-y-auto">
        <ClientOnly>
          <template v-for="(item, index) in visibleMenuItems" :key="item.path">
            <div v-if="item.separator && index > 0" class="pt-3 mt-3 border-t border-white/10"></div>
            <NuxtLink
              :to="item.path"
              class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition"
              :class="isActive(item.path) ? 'bg-white/15 text-white font-medium' : 'text-primary-200 hover:bg-white/10 hover:text-white'"
            >
              <span class="text-base">{{ item.icon }}</span>
              <span>{{ item.label }}</span>
            </NuxtLink>
          </template>
        </ClientOnly>
      </nav>

      <div class="p-4 border-t border-white/10">
        <button @click="handleLogout" class="flex items-center gap-2 text-sm text-primary-300 hover:text-white transition w-full px-3 py-2 rounded-lg hover:bg-white/10">
          <span>&#x1F6AA;</span>
          <span>退出登录</span>
        </button>
      </div>
    </aside>

    <div v-if="mobileOpen" class="fixed inset-0 bg-black/50 z-40 md:hidden" @click="mobileOpen = false"></div>

    <div class="flex-1 flex flex-col min-w-0">
      <header class="bg-white border-b border-gray-200 px-4 sm:px-6 py-3 flex items-center justify-between sticky top-0 z-10">
        <button class="md:hidden text-gray-500 hover:text-gray-700" @click="mobileOpen = !mobileOpen">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg>
        </button>

        <div class="flex items-center gap-3 ml-auto">
          <ClientOnly>
            <span
              class="text-xs font-medium px-2.5 py-1 rounded-full"
              :class="roleBadgeClass"
            >{{ userRoleLabel }}</span>
            <span class="text-sm text-gray-700 font-medium">{{ authStore.user?.username }}</span>
          </ClientOnly>
        </div>
      </header>

      <main class="flex-1 p-4 sm:p-6 overflow-y-auto">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { useRouter } from "vue-router";

const authStore = useAuthStore();
const router = useRouter();
const route = useRoute();
const mobileOpen = ref(false);

const roleMenuItems = {
  admin: [
    { path: "/", icon: "\u{1F4CA}", label: "工作台" },
    { path: "/admin/users", icon: "\u{1F465}", label: "人员管理" },
    { path: "/admin/student-tags", icon: "\u{1F3F7}", label: "学员标签" },
    { path: "/admin/departments", icon: "\u{1F3E2}", label: "部门管理" },
    { path: "/admin/libraries", icon: "\u{1F4DA}", label: "文档库管理" },
    { path: "/admin/approvals", icon: "\u{1F4DD}", label: "文档审批" },
    { path: "/admin/ai-prompts", icon: "\u{1F3A8}", label: "AI提示词" },
    { path: "/admin/question-banks", icon: "\u{1F4DA}", label: "题库管理" },
    { path: "/admin/study-materials", icon: "\u{1F4D6}", label: "学习资料", separator: true },
    { path: "/admin/videos", icon: "\u{1F3AC}", label: "视频资料" },
    { path: "/admin/exams", icon: "\u{1F4DD}", label: "试卷管理" },
    { path: "/profile", icon: "\u{2699}\u{FE0F}", label: "个人设置", separator: true },
  ],
  teacher: [
    { path: "/", icon: "\u{1F4CA}", label: "工作台" },
    { path: "/admin/libraries", icon: "\u{1F4DA}", label: "文档库管理" },
    { path: "/admin/approvals", icon: "\u{1F4DD}", label: "文档审批" },
    { path: "/admin/users", icon: "\u{1F393}", label: "学员管理" },
    { path: "/admin/student-tags", icon: "\u{1F3F7}", label: "学员标签" },
    { path: "/admin/question-banks", icon: "\u{1F4DA}", label: "题库管理" },
    { path: "/admin/study-materials", icon: "\u{1F4D6}", label: "学习资料", separator: true },
    { path: "/admin/videos", icon: "\u{1F3AC}", label: "视频资料" },
    { path: "/admin/exams", icon: "\u{1F4DD}", label: "试卷管理" },
    { path: "/profile", icon: "\u{2699}\u{FE0F}", label: "个人设置", separator: true },
  ],
  student: [
    { path: "/", icon: "\u{1F4CA}", label: "工作台" },
    { path: "/student/courses", icon: "\u{1F4D6}", label: "我的课程" },
    { path: "/student/videos", icon: "\u{1F3AC}", label: "我的学习视频" },
    { path: "/student/training", icon: "\u{1F3AF}", label: "模拟训练" },
    { path: "/student/exams", icon: "\u{1F4DD}", label: "我的考试" },
    { path: "/profile", icon: "\u{2699}\u{FE0F}", label: "个人设置", separator: true },
  ],
};

const visibleMenuItems = computed(() => {
  return roleMenuItems[authStore.user?.role] || roleMenuItems.student;
});

const userRoleLabel = computed(() => {
  const map = { admin: "管理员", teacher: "教师", student: "学员" };
  return map[authStore.user?.role] || "用户";
});

const roleBadgeClass = computed(() => {
  const map = {
    admin: "bg-accent-100 text-accent-700",
    teacher: "bg-primary-100 text-primary-700",
    student: "bg-green-100 text-green-700",
  };
  return map[authStore.user?.role] || "bg-gray-100 text-gray-600";
});

function isActive(path) {
  if (path === "/") return route.path === "/";
  return route.path.startsWith(path);
}

function handleLogout() {
  authStore.logout();
  router.push("/login");
}
</script>
