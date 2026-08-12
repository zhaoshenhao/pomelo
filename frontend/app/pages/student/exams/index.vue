<template>
  <div>
    <h2 class="text-xl font-bold text-gray-900 mb-6">我的考试</h2>

    <div class="mb-8">
      <h3 class="text-lg font-bold text-amber-700 mb-3">即将开始的考试</h3>
      <div v-if="upcoming.length === 0" class="text-sm text-gray-400">暂无</div>
      <div v-else class="space-y-3">
        <div v-for="e in upcoming" :key="e.assignment_id" class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <h4 class="text-sm font-bold text-gray-900">{{ e.name }}</h4>
          <p class="text-xs text-gray-500 mt-1">{{ e.description || '暂无描述' }}</p>
          <div class="flex gap-3 mt-2 text-xs text-gray-400">
            <span>时长：{{ e.duration_minutes }}分钟</span>
            <span>及格分：{{ e.pass_score }}</span>
            <span v-if="e.start_time">开始：{{ formatDt(e.start_time) }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="mb-8">
      <h3 class="text-lg font-bold text-primary-700 mb-3">进行中的考试</h3>
      <div v-if="in_progress.length === 0" class="text-sm text-gray-400">暂无</div>
      <div v-else class="space-y-3">
        <div v-for="e in in_progress" :key="e.assignment_id" class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <div class="flex items-center justify-between">
            <div><h4 class="text-sm font-bold text-gray-900">{{ e.name }}</h4><p class="text-xs text-gray-500 mt-1">{{ e.description || '暂无描述' }}</p><div class="flex gap-3 mt-2 text-xs text-gray-400"><span>时长：{{ e.duration_minutes }}分钟</span><span>截止：{{ e.end_time ? formatDt(e.end_time) : '不限' }}</span></div></div>
            <button @click="startExam(e.exam_id)" class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700">开始考试</button>
          </div>
        </div>
      </div>
    </div>

    <div class="mb-8">
      <h3 class="text-lg font-bold text-green-700 mb-3">已完成的考试</h3>
      <div v-if="completed.length === 0" class="text-sm text-gray-400">暂无</div>
      <div v-else class="space-y-3">
        <div v-for="e in completed" :key="e.assignment_id" class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <div class="flex items-center justify-between">
            <div><h4 class="text-sm font-bold text-gray-900">{{ e.name }}</h4><div class="flex gap-3 mt-2 text-xs"><span class="text-accent-600 font-bold">得分：{{ e.score }}</span><span :class="e.passed ? 'text-green-600' : 'text-red-500'">{{ e.passed ? '已通过' : '未通过' }}</span></div></div>
            <NuxtLink :to="`/student/exams/${e.exam_id}/view`" class="text-xs text-primary-600 hover:underline">查看细节</NuxtLink>
          </div>
        </div>
      </div>
    </div>

    <div>
      <h3 class="text-lg font-bold text-red-500 mb-3">过期的考试</h3>
      <div v-if="expired.length === 0" class="text-sm text-gray-400">暂无</div>
      <div v-else class="space-y-3">
        <div v-for="e in expired" :key="e.assignment_id" class="bg-white rounded-xl shadow-sm border border-red-200 p-4">
          <h4 class="text-sm font-bold text-gray-900">{{ e.name }}</h4>
          <p class="text-xs text-gray-500 mt-1">{{ e.description || '暂无描述' }}</p>
          <div class="flex gap-3 mt-2 text-xs"><span class="text-red-500 font-bold">得分：0（未参加）</span><span class="text-red-500">未通过</span></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
definePageMeta({ middleware: ["auth"] });
const { $api } = useNuxtApp();
const upcoming = ref([]); const in_progress = ref([]); const completed = ref([]); const expired = ref([]);

function formatDt(d) { if (!d) return ""; return d.substring(0, 16).replace("T", " "); }
function startExam(id) { window.open(`/exam/take/${id}`, "_blank", "width=1000,height=700"); }

async function fetchMy() {
  try {
    const r = await $api.get("/exams/my");
    upcoming.value = r.data.data.upcoming;
    in_progress.value = r.data.data.in_progress;
    completed.value = r.data.data.completed;
    expired.value = r.data.data.expired;
  } catch {}
}
fetchMy();
</script>
