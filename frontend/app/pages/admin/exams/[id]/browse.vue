<template>
  <div>
    <div class="mb-4">
      <NuxtLink to="/admin/exams" class="text-sm text-primary-600 hover:underline">&larr; 返回试卷列表</NuxtLink>
    </div>
    <div v-if="loadError" class="text-center py-12">
      <div class="text-gray-400 text-sm mb-3">加载失败，请重试</div>
      <button @click="fetchPaper()" class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700">重新加载</button>
    </div>
    <div v-else-if="!paper" class="text-center text-gray-400 py-20">加载中...</div>
    <div v-else>
      <div class="mb-6">
        <h2 class="text-xl font-bold text-gray-900">{{ paper.name }}</h2>
        <p class="text-sm text-gray-500 mt-1">{{ paper.description || '暂无描述' }}</p>
        <div class="flex flex-wrap items-center gap-3 mt-3 text-xs text-gray-400">
          <span>时长：{{ paper.duration_minutes }} 分钟</span>
          <span>及格分：{{ paper.pass_score }}</span>
          <span>题目数：{{ paper.questions.length }}</span>
        </div>
      </div>
      <div class="space-y-4">
        <div v-for="(q, idx) in paper.questions" :key="q.id" class="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
          <div class="flex items-start justify-between mb-3">
            <h3 class="text-sm font-bold text-gray-900">{{ idx + 1 }}. {{ typeLabel(q.type) }}</h3>
            <span class="text-xs px-2 py-0.5 rounded-full" :class="typeBadge(q.type)">{{ typeLabel(q.type) }}</span>
          </div>
          <p class="text-sm text-gray-700 mb-3">{{ q.question }}</p>
          <div v-if="q.type === 'single' || q.type === 'multiple'" class="space-y-1 mb-3">
            <div v-for="opt in q.options" :key="opt" class="text-sm px-3 py-1 rounded" :class="isCorrectOption(q, opt) ? 'bg-green-50 text-green-700 font-medium border border-green-200' : 'text-gray-600'">{{ opt }}</div>
          </div>
          <div v-if="q.type === 'match'" class="mb-3 grid grid-cols-2 gap-2 text-sm">
            <div v-for="(left, i) in q.left" :key="left" class="flex gap-2">
              <span class="font-medium text-gray-700">{{ left }}</span>
              <span class="text-green-700">&rarr; {{ matchAnswer(q, left) }}</span>
            </div>
          </div>
          <div class="text-xs bg-amber-50 text-amber-700 border border-amber-200 rounded-lg px-3 py-2">
            <span class="font-medium">答案：</span>{{ formatAnswer(q) }}
          </div>
          <div v-if="q.explanation" class="text-xs text-gray-500 mt-2">{{ q.explanation }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";

definePageMeta({ middleware: ["auth", "teacher"] });

const { $api } = useNuxtApp();
const route = useRoute();
const paper = ref(null);
const loadError = ref(false);

function typeLabel(t) { const m = { single: "单选", multiple: "多选", true_false: "对错", fill: "填空", match: "匹配" }; return m[t] || t; }
function typeBadge(t) { const m = { single: "bg-blue-50 text-blue-700 border-blue-200", multiple: "bg-purple-50 text-purple-700", true_false: "bg-amber-50 text-amber-700", fill: "bg-green-50 text-green-700", match: "bg-pink-50 text-pink-700" }; return m[t] || "bg-gray-50"; }

function isCorrectOption(q, opt) {
  const letter = opt.trim()[0];
  if (q.type === "single") return letter === q.answer;
  if (q.type === "multiple") return (q.answers || []).includes(letter);
  return false;
}

function formatAnswer(q) {
  if (q.type === "single") return q.answer;
  if (q.type === "multiple") return (q.answers || []).join(", ");
  if (q.type === "true_false") return q.answer ? "正确" : "错误";
  if (q.type === "fill") return q.answer;
  if (q.type === "match") return Object.entries(q.matches || {}).map(([k, v]) => `${k}→${v}`).join("  ");
  return "";
}

function matchAnswer(q, left) {
  if (!q.matches) return "";
  if (q.matches[left] !== undefined) return q.matches[left];
  const letter = (left || "").trim()[0];
  if (letter && q.matches[letter] !== undefined) return q.matches[letter];
  return "";
}

async function fetchPaper() {
  loadError.value = false;
  try { const r = await $api.get(`/exams/${route.params.id}/paper`); paper.value = r.data.data; } catch { loadError.value = true; }
}
onMounted(fetchPaper);
</script>
