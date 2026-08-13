<template>
  <div>
    <div class="mb-4 flex items-center justify-between">
      <NuxtLink to="/admin/videos" class="text-sm text-primary-600 hover:underline">&larr; 返回视频列表</NuxtLink>
      <button @click="confirmRegen = true" :disabled="regenerating" class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed">{{ regenerating ? '汇总中...' : '重新汇总' }}</button>
    </div>
    <h2 class="text-xl font-bold text-gray-900 mb-6">{{ stats?.video_name || '统计' }} - 统计</h2>

    <div v-if="loading" class="text-center text-gray-400 py-20">加载中...</div>

    <div v-if="message" class="mb-4 px-4 py-3 rounded-xl text-sm bg-red-50 text-red-700 border border-red-200">{{ message }}</div>

    <template v-if="stats">
      <div class="grid grid-cols-3 gap-4 mb-6">
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-center">
          <div class="text-2xl font-bold text-primary-600">{{ stats.total_viewers }}</div>
          <div class="text-xs text-gray-500 mt-1">看过人数</div>
        </div>
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-center">
          <div class="text-2xl font-bold text-primary-600">{{ stats.total_views }}</div>
          <div class="text-xs text-gray-500 mt-1">总次数</div>
        </div>
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-center">
          <div class="text-2xl font-bold text-primary-600">{{ fmtDur(stats.total_watch_seconds) }}</div>
          <div class="text-xs text-gray-500 mt-1">总观看时长</div>
        </div>
      </div>

      <div class="flex gap-4">
        <div class="w-1/3 shrink-0">
          <h3 class="text-sm font-bold text-gray-700 mb-2">观看记录</h3>
          <div v-if="viewRecords.length === 0" class="text-xs text-gray-400 py-8 text-center">暂无记录</div>
          <div v-else class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden max-h-[60vh] overflow-y-auto" @scroll="onViewScroll">
            <div v-for="(r, i) in viewRecords" :key="i" class="px-3 py-2 text-xs border-b border-gray-50" :class="i % 2 === 0 ? 'bg-white' : 'bg-gray-50'">{{ fmtMinute(r.watched_at) }} · {{ r.username }} · {{ fmtDur(r.watch_seconds) }}</div>
            <div v-if="viewLoading" class="px-3 py-2 text-xs text-gray-400 text-center">加载中...</div>
          </div>
        </div>
        <div class="flex-1">
          <h3 class="text-sm font-bold text-gray-700 mb-2">留言记录</h3>
          <div v-if="comments.length === 0" class="text-xs text-gray-400 py-8 text-center">暂无记录</div>
          <div v-else class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden max-h-[60vh] overflow-y-auto" @scroll="onCommentScroll">
            <div v-for="(c, i) in comments" :key="c.id" class="px-3 py-2 text-xs border-b border-gray-50 break-words whitespace-pre-wrap" :class="i % 2 === 0 ? 'bg-white' : 'bg-gray-50'">{{ fmtMinute(c.created_at) }} · {{ c.username }} · {{ c.content }}</div>
            <div v-if="commentLoading" class="px-3 py-2 text-xs text-gray-400 text-center">加载中...</div>
          </div>
        </div>
      </div>
    </template>

    <ConfirmModal :show="confirmRegen" title="确认重新汇总" message="将根据观看记录重新统计总次数和总观看时长，确定继续？" variant="danger" @confirm="regenerate" @cancel="confirmRegen = false" />

    <div v-if="regenerating" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/60">
      <div class="bg-white rounded-2xl shadow-xl px-8 py-6 text-center">
        <div class="inline-block w-8 h-8 border-4 border-primary-400 border-t-transparent rounded-full animate-spin mb-4"></div>
        <p class="text-sm text-gray-700 font-medium">正在重新汇总，请稍候...</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from "vue";
definePageMeta({ middleware: ["auth", "teacher"] });
const { $api } = useNuxtApp();
const route = useRoute();

const stats = ref(null);
const loading = ref(true);
const regenerating = ref(false);
const confirmRegen = ref(false);
const message = ref("");

const viewRecords = ref([]);
const viewPage = ref(1);
const viewTotal = ref(0);
const viewLoading = ref(false);

const comments = ref([]);
const commentPage = ref(1);
const commentTotal = ref(0);
const commentLoading = ref(false);

const PAGE_SIZE = 20;

function fmtDur(s) {
  if (!s) return "0:00";
  const m = Math.floor(s / 60);
  const r = s % 60;
  if (m < 60) return `${m}:${String(r).padStart(2, "0")}`;
  const h = Math.floor(m / 60);
  return `${h}时${m % 60}分`;
}

function fmtMinute(t) {
  if (!t) return "";
  const d = new Date(t);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

async function fetchStats(keepVisible = false) {
  if (!keepVisible) loading.value = true;
  try {
    const r = await $api.get(`/videos/${route.params.id}/stats`, { params: { page: 1, page_size: PAGE_SIZE } });
    const d = r.data.data;
    stats.value = d.stats;
    viewRecords.value = d.view_records.items || [];
    viewTotal.value = d.view_records.total || 0;
    comments.value = d.comments.items || [];
    commentTotal.value = d.comments.total || 0;
  } catch {} finally {
    if (!keepVisible) loading.value = false;
  }
}

async function regenerate() {
  confirmRegen.value = false;
  regenerating.value = true;
  try {
    await $api.post(`/videos/${route.params.id}/stats/regenerate`);
    await fetchStats(true);
    await nextTick();
  } catch (e) {
    message.value = e.response?.data?.detail || "重新汇总失败";
  } finally {
    regenerating.value = false;
  }
}

async function loadMoreViews() {
  if (viewLoading.value || viewRecords.value.length >= viewTotal.value) return;
  viewLoading.value = true;
  viewPage.value++;
  try {
    const r = await $api.get(`/videos/${route.params.id}/stats`, { params: { page: viewPage.value, page_size: PAGE_SIZE } });
    const items = r.data.data.view_records.items || [];
    viewRecords.value.push(...items);
  } catch { viewPage.value--; } finally {
    viewLoading.value = false;
  }
}

async function loadMoreComments() {
  if (commentLoading.value || comments.value.length >= commentTotal.value) return;
  commentLoading.value = true;
  commentPage.value++;
  try {
    const r = await $api.get(`/videos/${route.params.id}/stats`, { params: { page: commentPage.value, page_size: PAGE_SIZE } });
    const items = r.data.data.comments.items || [];
    comments.value.push(...items);
  } catch { commentPage.value--; } finally {
    commentLoading.value = false;
  }
}

function onViewScroll(e) {
  const el = e.target;
  if (el.scrollHeight - el.scrollTop - el.clientHeight < 40) {
    loadMoreViews();
  }
}

function onCommentScroll(e) {
  const el = e.target;
  if (el.scrollHeight - el.scrollTop - el.clientHeight < 40) {
    loadMoreComments();
  }
}

fetchStats();
</script>
