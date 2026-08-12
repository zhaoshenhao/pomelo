<template>
  <div>
    <h2 class="text-xl font-bold text-gray-900 mb-6">我的学习视频</h2>
    <div v-if="items.length === 0" class="text-sm text-gray-400">暂无视频资料</div>
    <div v-else class="space-y-3">
      <div v-for="v in items" :key="v.id" class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <div class="flex items-center justify-between">
          <div class="flex-1">
            <h4 class="text-sm font-bold text-gray-900">{{ v.name }}</h4>
            <p class="text-xs text-gray-500 mt-1">{{ v.description || '暂无描述' }}</p>
            <div class="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-gray-400">
              <span>文档库：{{ v.library_name || '-' }}</span>
              <span>时长：{{ fmtDur(v.duration_seconds) }}</span>
              <span v-if="v.last_watched_at">上次观看：{{ fmtTs(v.last_watched_at) }}</span>
            </div>
            <div class="flex gap-3 mt-1 text-xs">
              <span :class="v.watched ? 'text-green-600' : 'text-gray-400'">{{ v.watched ? '已观看' : '未观看' }}</span>
              <span class="text-gray-500">累计 {{ fmtDur(v.my_watch_seconds) }} · {{ v.my_views }} 次</span>
            </div>
          </div>
          <button @click="playVideo(v.id)" class="ml-4 px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 shrink-0">播放</button>
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

function fmtDur(s) { if (!s) return "0:00"; const m = Math.floor(s/60); const r = s%60; return `${m}:${String(r).padStart(2,"0")}`; }
function fmtTs(t) { if (!t) return ""; return t.substring(0,16).replace("T"," "); }
function playVideo(id) { window.open(`/student/videos/play/${id}`, "_blank", "width=1024,height=640"); }

async function fetchMy() {
  try { const r = await $api.get("/videos/my/list"); items.value = r.data.data || []; } catch {}
}
fetchMy();
</script>
