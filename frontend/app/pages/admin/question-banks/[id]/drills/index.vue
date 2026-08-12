<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <NuxtLink to="/admin/question-banks" class="text-xs text-primary-600 hover:underline">&larr; 返回题库管理</NuxtLink>
        <h2 class="text-xl font-bold text-gray-900 mt-1">{{ summary?.qb_name || '训练汇总' }}</h2>
      </div>
      <button @click="regenerate" :disabled="regenerating" class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50">{{ regenerating ? '汇总中...' : '重新汇总' }}</button>
    </div>

    <div v-if="loading" class="px-4 py-12 text-center text-gray-400 text-sm">加载中...</div>
    <div v-else-if="error" class="px-4 py-12 text-center text-gray-400 text-sm">{{ error }}</div>

    <template v-else-if="summary">
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-center">
          <div class="text-2xl font-bold text-primary-600">{{ summary.total_students }}</div>
          <div class="text-xs text-gray-500 mt-1">训练学生数</div>
        </div>
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-center">
          <div class="text-2xl font-bold text-primary-600">{{ summary.used_questions }}</div>
          <div class="text-xs text-gray-500 mt-1">被使用题目数</div>
        </div>
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-center">
          <div class="text-2xl font-bold text-primary-600">{{ summary.total_attempts }}</div>
          <div class="text-xs text-gray-500 mt-1">总测试题数</div>
        </div>
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-center">
          <div class="text-2xl font-bold text-primary-600">{{ summary.ever_correct_questions }}</div>
          <div class="text-xs text-gray-500 mt-1">曾答对题目数</div>
        </div>
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-center">
          <div class="text-2xl font-bold" :class="summary.accuracy >= 60 ? 'text-green-600' : 'text-red-500'">{{ summary.accuracy }}%</div>
          <div class="text-xs text-gray-500 mt-1">正确率</div>
        </div>
      </div>

      <div v-if="message" class="text-xs text-green-600 mb-2">{{ message }}</div>
      <div class="text-xs text-gray-400 mb-2">汇总时间：{{ formatDate(summary.updated_at) }}</div>

      <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-left text-gray-600">
            <tr>
              <th class="px-4 py-3 font-medium">#</th>
              <th class="px-4 py-3 font-medium">题目</th>
              <th class="px-4 py-3 font-medium">题型</th>
              <th class="px-4 py-3 font-medium">总次数</th>
              <th class="px-4 py-3 font-medium">正确率</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="(q, idx) in summary.questions" :key="q.question_id" class="hover:bg-gray-50 transition">
              <td class="px-4 py-2 text-gray-400 text-xs">{{ idx + 1 }}</td>
              <td class="px-4 py-2 text-gray-900 max-w-md truncate" :title="q.question">{{ q.question }}</td>
              <td class="px-4 py-2 text-gray-500 text-xs">{{ TYPE_NAMES[q.type] || q.type }}</td>
              <td class="px-4 py-2 text-gray-700">{{ q.total_attempts }}</td>
              <td class="px-4 py-2">
                <span v-if="q.total_attempts > 0" class="text-xs" :class="q.accuracy >= 60 ? 'text-green-600' : 'text-red-500'">{{ q.accuracy }}%</span>
                <span v-else class="text-xs text-gray-300">-</span>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="summary.questions.length === 0" class="px-4 py-12 text-center text-gray-400 text-sm">暂无题目数据</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref } from "vue";
definePageMeta({ middleware: ["auth", "teacher"] });
const { $api } = useNuxtApp();
const route = useRoute();

const summary = ref(null);
const loading = ref(true);
const error = ref("");
const regenerating = ref(false);
const message = ref("");

const TYPE_NAMES = { single: "单选", multiple: "多选", true_false: "判断", fill: "填空", match: "匹配" };

function formatDate(d) {
  if (!d) return "";
  return d.substring(0, 19).replace("T", " ");
}

async function fetchSummary() {
  loading.value = true;
  error.value = "";
  try {
    const r = await $api.get(`/drills/banks/${route.params.id}/summary`);
    summary.value = r.data.data;
  } catch (e) {
    error.value = e.response?.data?.detail || "加载失败";
  } finally {
    loading.value = false;
  }
}

async function regenerate() {
  regenerating.value = true;
  try {
    const r = await $api.post(`/drills/banks/${route.params.id}/summary/regenerate`);
    summary.value = r.data.data;
    error.value = "";
    message.value = "已重新汇总";
    setTimeout(() => { message.value = ""; }, 2000);
  } catch (e) {
    error.value = e.response?.data?.detail || "汇总失败";
  } finally {
    regenerating.value = false;
  }
}

fetchSummary();
</script>
