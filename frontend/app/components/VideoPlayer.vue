<template>
  <div class="group h-screen w-screen bg-black relative" :class="{ 'select-none': !examDebug }" @contextmenu="blockCtx" @copy="blockCtx" @selectstart="blockCtx">
    <video ref="videoEl" :src="videoUrl" autoplay controls playsinline controlsList="nodownload"
           class="w-full h-full object-contain" @canplay="tryAutoplay" @ended="onEnded"></video>

    <div class="absolute top-4 right-4 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
      <button @click="seek(-10)" title="后退10秒" class="w-10 h-10 rounded-full bg-black/60 hover:bg-black/80 text-white flex items-center justify-center text-lg">&#x23EA;</button>
      <button @click="seek(10)" title="前进10秒" class="w-10 h-10 rounded-full bg-black/60 hover:bg-black/80 text-white flex items-center justify-center text-lg">&#x23E9;</button>
      <button @click="showComments = !showComments" title="留言" class="w-10 h-10 rounded-full bg-black/60 hover:bg-black/80 text-white flex items-center justify-center text-lg">&#x1F4AC;</button>
      <button @click="confirmExit = true" title="退出" class="w-10 h-10 rounded-full bg-red-500/70 hover:bg-red-500 text-white flex items-center justify-center text-lg">&#x2715;</button>
    </div>

    <div v-if="showComments" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60" @click.self="showComments = false">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 h-[70vh] flex flex-col">
        <div class="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
          <span class="font-bold text-gray-900 text-sm">留言</span>
          <button @click="showComments = false" class="text-gray-400 hover:text-gray-600 text-sm">关闭</button>
        </div>
        <div class="p-3 border-b border-gray-100">
          <input v-model="newComment" @keyup.enter="addComment" placeholder="输入留言，按回车发送..." class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" :disabled="commentSending" />
        </div>
        <div class="flex-1 overflow-y-auto p-3 space-y-3">
          <div v-for="c in comments" :key="c.id" class="border-b border-gray-50 pb-2">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-xs font-medium text-gray-700">{{ c.username }}</span>
              <span class="text-xs text-gray-400" :title="fullTime(c.created_at)">{{ fmtCommentTime(c.created_at) }}</span>
            </div>
            <div class="text-xs text-gray-600 whitespace-pre-wrap break-words">{{ c.content }}</div>
          </div>
          <div v-if="!comments.length" class="text-xs text-gray-400 text-center py-8">暂无留言</div>
        </div>
      </div>
    </div>

    <div v-if="confirmExit" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm mx-4 p-6 text-center">
        <h3 class="text-lg font-bold text-gray-900 mb-2">退出播放？</h3>
        <p class="text-sm text-gray-500 mb-4">退出后将记录本次观看时长。</p>
        <div class="flex gap-3">
          <button @click="doExit" class="flex-1 py-2 bg-red-500 text-white text-sm rounded-lg hover:bg-red-600">退出</button>
          <button @click="confirmExit = false" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50">继续观看</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";

const props = defineProps({
  videoId: { type: Number, required: true },
  recordStats: { type: Boolean, default: false },
});

const { $api } = useNuxtApp();
const runtime = useRuntimeConfig();
const examDebug = runtime.public.examDebug === "true";

const videoUrl = ref("");
const videoEl = ref(null);
const watchSeconds = ref(0);
let watchTimer = null;

const showComments = ref(false);
const comments = ref([]);
const newComment = ref("");
const commentSending = ref(false);

const confirmExit = ref(false);

function blockCtx(e) { if (!examDebug) e.preventDefault(); }
function tryAutoplay() { if (videoEl.value) videoEl.value.play().catch(() => {}); }
function onEnded() { clearInterval(watchTimer); }
function seek(s) { if (videoEl.value) videoEl.value.currentTime = Math.max(0, videoEl.value.currentTime + s); }

function fmtCommentTime(t) {
  if (!t) return "";
  const d = new Date(t);
  const now = new Date();
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  }
  return `${d.getMonth() + 1}-${String(d.getDate()).padStart(2, "0")}`;
}
function fullTime(t) {
  if (!t) return "";
  const d = new Date(t);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

async function loadComments() {
  try {
    const r = await $api.get(`/videos/${props.videoId}/comments`, { params: { page_size: 50 } });
    comments.value = r.data.data.items || [];
  } catch {}
}

async function addComment() {
  if (!newComment.value.trim() || commentSending.value) return;
  commentSending.value = true;
  try {
    await $api.post(`/videos/${props.videoId}/comments`, { content: newComment.value.trim() });
    newComment.value = "";
    await loadComments();
  } catch {} finally { commentSending.value = false; }
}

async function doExit() {
  clearInterval(watchTimer);
  if (props.recordStats && watchSeconds.value > 0) {
    try { await $api.post(`/videos/${props.videoId}/watch`, { watch_seconds: watchSeconds.value }); } catch {}
  }
  confirmExit.value = false;
  try { window.close(); } catch {}
}

onMounted(async () => {
  try {
    const r = await $api.get(`/videos/${props.videoId}/play-url`);
    videoUrl.value = r.data.data.url;
  } catch {}
  watchTimer = setInterval(() => {
    if (videoEl.value && !videoEl.value.paused) watchSeconds.value++;
  }, 1000);
  loadComments();
});

onUnmounted(() => { clearInterval(watchTimer); });
</script>
