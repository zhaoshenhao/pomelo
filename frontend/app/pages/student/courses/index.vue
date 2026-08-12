<template>
  <div>
    <h2 class="text-xl font-bold text-gray-900 mb-6">我的课程</h2>
    <div v-if="items.length === 0" class="text-sm text-gray-400">暂无课程</div>
    <div v-else class="space-y-3">
      <div v-for="e in items" :key="e.material_id" class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <div class="flex items-center justify-between">
          <div class="flex-1">
            <h4 class="text-sm font-bold text-gray-900">{{ e.material_name }}</h4>
            <p class="text-xs text-gray-500 mt-1">{{ e.material_description || '暂无描述' }}</p>
            <div class="flex gap-3 mt-2 text-xs text-gray-400">
              <span>文档：{{ e.document_names || '-' }}</span>
              <span>最少阅读：{{ e.min_minutes }}分钟</span>
              <span v-if="e.last_study_at">上次学习：{{ e.last_study_at.substring(0,16).replace('T',' ') }}</span>
            </div>
            <div class="flex gap-3 mt-1 text-xs">
              <span :class="e.has_started ? 'text-green-600' : 'text-gray-400'">{{ e.has_started ? '已阅读' : '未阅读' }}</span>
              <span :class="e.completed ? 'text-green-600' : 'text-gray-400'">{{ e.completed ? '已完成' : '未完成' }}</span>
              <span v-if="e.has_started" class="text-gray-500">已学 {{ Math.floor(e.total_study_seconds/60) }} 分钟</span>
              <span class="text-gray-400">阅读 {{ e.read_count }} 次 | 完成 {{ e.complete_count }} 次</span>
            </div>
          </div>
          <button @click="startRead(e.material_id)" class="ml-4 px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 shrink-0">{{ e.has_started && !e.completed ? '继续学习' : e.completed ? '重新阅读' : '开始阅读' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";

definePageMeta({ middleware: ["auth"] });

const { $api } = useNuxtApp();
const items = ref([]);

function startRead(material_id) { window.open(`/student/courses/read/${material_id}`, "_blank", "width=1050,height=750"); }

async function fetchMy() {
  try { const res = await $api.get("/study-assignments/my"); items.value = res.data.data.items; } catch {}
}
fetchMy();
</script>
