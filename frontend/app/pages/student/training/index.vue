<template>
  <div>
    <div class="mb-6">
      <h2 class="text-xl font-bold text-gray-900">模拟训练</h2>
      <p class="text-sm text-gray-500 mt-1">选择题库进行练习，系统会根据训练记录智能选题</p>
    </div>

    <div v-if="loading" class="px-4 py-12 text-center text-gray-400 text-sm">加载中...</div>

    <template v-else>
      <div v-if="banks.length === 0" class="px-4 py-12 text-center text-gray-400 text-sm">暂无可用题库</div>

      <div v-else class="space-y-3">
        <div v-for="b in banks" :key="b.id" class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 hover:shadow-md transition">
          <div class="flex items-center justify-between">
            <div class="flex-1 min-w-0">
              <h3 class="font-bold text-gray-900 mb-1 truncate">{{ b.name }}</h3>
              <p class="text-xs text-gray-400 mb-1 truncate">{{ b.description || '暂无描述' }}</p>
              <div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
                <span>题目数：<span class="font-semibold text-gray-900">{{ b.question_count }}</span></span>
                <span>{{ formatTypeCounts(b.type_counts) }}</span>
                <template v-if="b.total_answered > 0">
                  <span>已答 {{ b.total_answered }} 题</span>
                  <span>正确率 {{ b.accuracy }}%</span>
                  <span>曾答对 {{ b.ever_correct_questions }} 题</span>
                </template>
                <span v-else class="text-gray-400">尚未训练</span>
              </div>
            </div>
            <button @click="startDrill(b)" :disabled="b.question_count === 0" class="ml-4 px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition shrink-0">开始训练</button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref } from "vue";
definePageMeta({ middleware: ["auth"] });
const { $api } = useNuxtApp();

const banks = ref([]);
const loading = ref(true);

const TYPE_NAMES = { single: "单选", multiple: "多选", true_false: "判断", fill: "填空", match: "匹配" };

function formatTypeCounts(tc) {
  if (!tc || Object.keys(tc).length === 0) return "暂无题目";
  return Object.entries(tc).map(([k, v]) => `${TYPE_NAMES[k] || k} ${v}`).join("  ");
}

function startDrill(b) {
  window.open(`/student/training/${b.id}`, "_blank", "width=1000,height=700");
}

async function fetchBanks() {
  loading.value = true;
  try {
    const r = await $api.get("/drills/banks");
    banks.value = r.data.data || [];
  } catch {} finally {
    loading.value = false;
  }
}

fetchBanks();
</script>
