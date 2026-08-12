<template>
  <div>
    <div class="mb-4">
      <NuxtLink to="/student/exams" class="text-sm text-primary-600 hover:underline">&larr; 返回我的考试</NuxtLink>
    </div>
    <div v-if="!result" class="text-center text-gray-400 py-20">加载中...</div>
    <div v-else>
      <h2 class="text-xl font-bold text-gray-900 mb-2">{{ result.exam_name || '考试详情' }}</h2>
      <div class="flex gap-4 mb-6 text-sm">
        <span class="text-green-600 font-bold text-lg">得分：{{ result.score }} / 100</span>
        <span :class="result.passed ? 'text-green-600' : 'text-red-500'" class="text-lg font-bold">{{ result.passed ? '通过' : '未通过' }}</span>
        <span class="text-gray-500">正确：{{ result.correct }} / {{ result.total }}</span>
      </div>
      <div class="space-y-3 mb-6">
        <div v-for="r in result.results" :key="r.question_id" class="bg-white rounded-xl shadow-sm border p-4" :class="r.correct ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'">
          <div class="flex items-center gap-2 mb-2">
            <span class="text-xs font-bold text-gray-700">{{ r.question_id }}</span>
            <span class="text-xs text-gray-400">{{ typeLabel(qMap[r.question_id]?.type) }}</span>
            <span class="text-xs px-2 py-0.5 rounded-full" :class="r.correct ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-500'">{{ r.correct ? '正确' : '错误' }}</span>
          </div>
          <div class="text-sm text-gray-800 mb-2">{{ qMap[r.question_id]?.question || r.question_id }}</div>

          <template v-if="qMap[r.question_id]">
            <div v-if="qMap[r.question_id].type === 'single'" class="text-xs space-y-1 mb-2">
              <div v-for="opt in qMap[r.question_id].options" :key="opt" :class="opt[0] === r.actual ? 'text-primary-700 font-medium bg-primary-50 -mx-1 px-1 py-0.5 rounded' : 'text-gray-500'">{{ opt }}</div>
            </div>
            <div v-else-if="qMap[r.question_id].type === 'multiple'" class="text-xs space-y-1 mb-2">
              <div v-for="opt in qMap[r.question_id].options" :key="opt" :class="(r.actual || []).includes(opt[0]) ? 'text-primary-700 font-medium bg-primary-50 -mx-1 px-1 py-0.5 rounded' : 'text-gray-500'">{{ opt }}</div>
            </div>
            <div v-else-if="qMap[r.question_id].type === 'match'" class="text-xs space-y-0.5 mb-2">
              <div v-for="left in qMap[r.question_id].left" :key="left" class="flex gap-1"><span class="text-gray-600">{{ left }}</span><span class="text-gray-400">→</span><span class="font-medium text-primary-700">{{ (r.actual || {})[left] || '未选' }}</span></div>
            </div>
          </template>

          <div v-if="qMap[r.question_id]?.type === 'true_false'" class="text-xs text-gray-500 mt-1">你的答案：<span class="font-medium" :class="r.actual === true ? 'text-primary-700' : 'text-red-500'">{{ r.actual === true ? '正确' : r.actual === false ? '错误' : '未答' }}</span></div>
          <div v-else-if="qMap[r.question_id]?.type === 'fill'" class="text-xs text-gray-500 mt-1">你的答案：<span class="font-medium" :class="r.correct ? 'text-green-700' : 'text-red-500'">{{ r.actual || '未答' }}</span></div>
        </div>
      </div>
      <div v-if="result.evaluation" class="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-700">
        <h3 class="font-bold text-sm mb-1">AI 评价与建议</h3>
        <p class="text-xs">{{ result.evaluation }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";

definePageMeta({ middleware: ["auth"] });

const { $api } = useNuxtApp();
const route = useRoute();

const result = ref(null);

const qMap = computed(() => {
  if (!result.value?.questions) return {};
  const m = {};
  for (const q of result.value.questions) { m[q.id] = q; }
  return m;
});

function typeLabel(t) {
  const m = { single: "单选", multiple: "多选", true_false: "对错", fill: "填空", match: "匹配" };
  return m[t] || t || "";
}

async function fetchResult() {
  try { const r = await $api.get(`/exams/${route.params.id}/my-result`); result.value = r.data.data; } catch {}
}
fetchResult();
</script>
