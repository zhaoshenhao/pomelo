<template>
  <div>
    <div class="mb-4"><NuxtLink to="/admin/study-materials" class="text-sm text-primary-600 hover:underline">&larr; 返回学习资料列表</NuxtLink></div>
    <h2 class="text-xl font-bold text-gray-900 mb-6">{{ stats?.material_name || '统计' }} - 学习统计</h2>

    <div v-if="loading" class="text-center text-gray-400 py-20">加载中...</div>

    <template v-else-if="stats">
      <div class="grid grid-cols-5 gap-4 mb-6">
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-center">
          <div class="text-2xl font-bold text-primary-600">{{ stats.students_viewed }}</div>
          <div class="text-xs text-gray-500 mt-1">看过学生数</div>
        </div>
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-center">
          <div class="text-2xl font-bold text-green-600">{{ stats.students_completed }}</div>
          <div class="text-xs text-gray-500 mt-1">完成学生数</div>
        </div>
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-center">
          <div class="text-2xl font-bold text-primary-600">{{ stats.total_open_count }}</div>
          <div class="text-xs text-gray-500 mt-1">总打开次数</div>
        </div>
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-center">
          <div class="text-2xl font-bold text-primary-600">{{ fmtDur(stats.avg_watch_seconds) }}</div>
          <div class="text-xs text-gray-500 mt-1">平均观看时长</div>
        </div>
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-center">
          <div class="text-2xl font-bold text-primary-600">{{ fmtDur(stats.total_watch_seconds) }}</div>
          <div class="text-xs text-gray-500 mt-1">总观看时长</div>
        </div>
      </div>

      <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div class="px-4 py-3 border-b border-gray-100"><h3 class="text-sm font-bold text-gray-700">学生学习情况</h3></div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-gray-50 text-left text-gray-600">
              <tr>
                <th class="px-4 py-3 font-medium">名字</th>
                <th class="px-4 py-3 font-medium">是否看过</th>
                <th class="px-4 py-3 font-medium">是否完成</th>
                <th class="px-4 py-3 font-medium">总观看时长</th>
                <th class="px-4 py-3 font-medium">总阅读次数</th>
                <th class="px-4 py-3 font-medium">总完成次数</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="s in students" :key="s.student_id" class="hover:bg-gray-50 transition">
                <td class="px-4 py-3 font-medium text-gray-900">{{ s.name }}</td>
                <td class="px-4 py-3">
                  <span :class="s.viewed ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-400'" class="px-2 py-0.5 rounded-full text-xs font-medium">{{ s.viewed ? '已看过' : '未看过' }}</span>
                </td>
                <td class="px-4 py-3">
                  <span :class="s.completed ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-400'" class="px-2 py-0.5 rounded-full text-xs font-medium">{{ s.completed ? '已完成' : '未完成' }}</span>
                </td>
                <td class="px-4 py-3 text-gray-500">{{ fmtDur(s.total_study_seconds) }}</td>
                <td class="px-4 py-3 text-gray-500">{{ s.read_count }}</td>
                <td class="px-4 py-3 text-gray-500">{{ s.complete_count }}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="students.length === 0" class="px-4 py-12 text-center text-gray-400 text-sm">暂无学生</div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref } from "vue";
definePageMeta({ middleware: ["auth", "teacher"] });
const { $api } = useNuxtApp();
const route = useRoute();

const stats = ref(null);
const students = ref([]);
const loading = ref(true);

function fmtDur(s) {
  if (!s) return "0:00";
  const n = Math.round(s);
  const m = Math.floor(n / 60);
  const r = n % 60;
  if (m < 60) return `${m}:${String(r).padStart(2, "0")}`;
  const h = Math.floor(m / 60);
  return `${h}时${m % 60}分`;
}

async function fetchSummary() {
  loading.value = true;
  try {
    const r = await $api.get(`/study-materials/${route.params.id}/summary`);
    const d = r.data.data;
    stats.value = d.stats;
    students.value = d.students || [];
  } catch {} finally {
    loading.value = false;
  }
}

fetchSummary();
</script>
