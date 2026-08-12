<template>
  <div class="h-screen flex flex-col bg-gray-100" :class="{ 'select-none': !examDebug }" @contextmenu="blockCtx" @copy="blockCtx" @selectstart="blockCtx">
    <div v-if="loadError" class="flex-1 flex items-center justify-center text-gray-400 text-sm">加载失败，请关闭此窗口后重试。</div>
    <div v-else-if="state === 'intro'" class="flex-1 flex items-center justify-center">
      <div class="bg-white rounded-2xl shadow-xl p-8 max-w-md mx-4 text-center">
        <h1 class="text-2xl font-bold text-gray-900 mb-2">{{ info?.material_name }}</h1>
        <p class="text-sm text-gray-500 mb-4">{{ info?.material_description || '暂无描述' }}</p>
        <div class="text-sm text-gray-600 space-y-1 mb-6"><div>最少阅读时间：{{ info?.min_minutes }} 分钟</div><div v-if="info?.total_study_seconds">已累计：{{ Math.floor((info.total_study_seconds||0)/60) }} 分钟</div></div>
        <button @click="startRead" class="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-lg font-bold">{{ info?.completed ? '重新阅读' : '开始学习' }}</button>
      </div>
    </div>
    <div v-else-if="state === 'reading'" class="flex-1 flex flex-col overflow-hidden">
      <div class="px-4 py-2 bg-gray-50 border-b border-gray-200 flex items-center justify-between text-xs">
        <div class="flex items-center gap-2"><button @click="prevPage" :disabled="currentIndex <= 0" class="px-2 py-1 border border-gray-200 rounded hover:bg-gray-50 disabled:opacity-40">&larr;</button><span>{{ currentIndex+1 }}/{{ pages.length }}</span><button @click="nextPage" :disabled="currentIndex >= pages.length - 1" class="px-2 py-1 border border-gray-200 rounded hover:bg-gray-50 disabled:opacity-40">&rarr;</button></div>
        <div class="flex items-center gap-3">
          <span class="text-gray-400">{{ pageTypeLabel }}</span>
          <span class="text-gray-500">{{ currentPage?.title }}</span>
          <label class="flex items-center gap-1 cursor-pointer select-none"><input type="checkbox" v-model="autoTurn" class="w-3 h-3 rounded" /> 自动翻页</label>
          <label class="flex items-center gap-1 cursor-pointer select-none"><input type="checkbox" v-model="reading" class="w-3 h-3 rounded" /> 朗读</label>
        </div>
        <div class="flex items-center gap-2"><span class="text-accent-600 font-bold">已学 {{ Math.floor(elapsedMinutes) }} 分钟</span><button v-if="canComplete" @click="doComplete" class="px-3 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700">完成课程</button></div>
      </div>
      <div class="flex-1 flex overflow-hidden">
        <div class="w-52 border-r border-gray-200 overflow-y-auto bg-gray-50 flex-shrink-0">
          <div v-for="(p,idx) in pages" :key="idx"
            @click="sidebarCanClick ? loadPage(idx) : null"
            class="px-3 py-2 text-xs border-b border-gray-100 transition"
            :class="idx===currentIndex ? 'bg-white text-primary-700 font-medium border-l-2 border-l-primary-600' : (sidebarCanClick ? 'text-gray-600 cursor-pointer hover:bg-white' : 'text-gray-400 cursor-default')">
            <span class="text-[10px] text-gray-400 mr-1">{{ pageShort(p.type) }}</span>
            {{ p.title || (p.type==='cover'?'封面':p.type==='end'?'结束':'第'+p.chapter+'章') }}
          </div>
        </div>
        <div class="flex-1 overflow-auto"><div v-if="loadingPage" class="flex items-center justify-center h-full text-gray-400 text-sm">加载中...</div><div v-else class="h-full"><iframe v-if="pageHtmlContent" :srcdoc="pageHtmlContent" class="w-full h-full border-0" sandbox="allow-same-origin"></iframe></div></div>
      </div>
    </div>
    <div v-else-if="state === 'done'" class="flex-1 flex items-center justify-center">
      <div class="bg-white rounded-2xl shadow-xl p-8 max-w-md mx-4 text-center"><h2 class="text-xl font-bold text-gray-900 mb-4">恭喜完成学习</h2><p class="text-sm text-gray-500 mb-4">本次学习已达标，课程已完成。</p><button @click="closeWindow" class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">关闭窗口</button></div>
    </div>
    <audio ref="audioEl" class="hidden"></audio>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from "vue";

definePageMeta({ layout: false });

const { $api } = useNuxtApp();
const route = useRoute();
const runtime = useRuntimeConfig();
const examDebug = runtime.public.examDebug === "true";

const state = ref("intro"); const info = ref(null); const pages = ref([]);
const currentIndex = ref(0); const pageHtmlContent = ref(""); const pageTextContent = ref(""); const loadingPage = ref(false);
const sessionSeconds = ref(0); const totalSeconds = ref(0); const minMinutes = ref(10);
const isCompleted = ref(false); const loadError = ref(false); const assignId = ref(null);
const autoTurn = ref(true); const reading = ref(false); const audioEl = ref(null);
let timer; let progressTimer; let turnTimer;

const sidebarCanClick = computed(() => isCompleted.value || (info.value?.total_study_seconds || 0) > 0);
const elapsedMinutes = computed(() => Math.floor((totalSeconds.value + sessionSeconds.value) / 60));
const canComplete = computed(() => isLastPage.value && !isCompleted.value && elapsedMinutes.value >= minMinutes.value);
const isLastPage = computed(() => currentIndex.value >= pages.value.length - 1);
const currentPage = computed(() => pages.value[currentIndex.value]);
const pageTypeLabel = computed(() => { const m = { cover: "封面", chapter_cover: "章节封面", page: "内容页", end: "结束页" }; return m[currentPage.value?.type] || ""; });
function pageShort(t) { const m = { cover: "封面", chapter_cover: "章", page: "页", end: "结束" }; return m[t] || ""; }

function blockCtx(e) { if (!examDebug) e.preventDefault(); }
function closeWindow() { try { window.close(); } catch {} }

function estimateDuration(text) { if (!text) return 5; return Math.max(2, text.length / 4.5); }
function clearTurnTimer() { if (turnTimer) { clearTimeout(turnTimer); turnTimer = null; } }
function resetTurnTimer() {
  clearTurnTimer();
  if (!autoTurn.value) return;
  const p = currentPage.value;
  const dur = p?.audio_duration || estimateDuration(pageTextContent.value);
  turnTimer = setTimeout(() => {
    if (currentIndex.value >= pages.value.length - 1) return;
    loadPage(currentIndex.value + 1);
  }, (dur + 0.3) * 1000);
}

function startAudio() {
  if (!reading.value) return;
  const p = currentPage.value;
  if (!p?.audio_file) return;
  const ad = audioEl.value; if (ad) { ad.pause(); ad.src = ""; }
  $api.get(`/study-assignments/${assignId.value}/audio/${encodeURIComponent(p.audio_file)}`, { responseType: "blob" }).then((res) => {
    if (reading.value && currentPage.value?.audio_file === p.audio_file && audioEl.value) {
      const url = URL.createObjectURL(res.data);
      audioEl.value.src = url;
      audioEl.value.play().catch(() => {});
    }
  });
}

async function fetchInfo() {
  loadError.value = false;
  try {
    const r = await $api.get("/study-assignments/start", { params: { material_id: route.params.material_id } });
    info.value = r.data.data; assignId.value = r.data.data.id;
    pages.value = r.data.data.pages; totalSeconds.value = r.data.data.total_study_seconds || 0;
    minMinutes.value = r.data.data.min_minutes; isCompleted.value = r.data.data.completed || false;
    if (pages.value.length > 0) loadPage(0);
  } catch { loadError.value = true; }
}

function startRead() { state.value = "reading"; timer = setInterval(() => { sessionSeconds.value++; }, 1000); if (!isCompleted.value) startProgressLoop(); resetTurnTimer(); }
function startProgressLoop() {
  progressTimer = setInterval(async () => {
    if (state.value !== "reading" || isCompleted.value) return;
    try { await $api.post(`/study-assignments/${assignId.value}/progress`, { seconds: 30 }); totalSeconds.value += 30; sessionSeconds.value = Math.max(0, sessionSeconds.value - 30); } catch {}
  }, 30000);
}

async function reportProgress() { if (isCompleted.value || !assignId.value) return; try { await $api.post(`/study-assignments/${assignId.value}/progress`, { seconds: sessionSeconds.value }); totalSeconds.value += sessionSeconds.value; sessionSeconds.value = 0; } catch {} }

async function loadPage(idx) {
  clearTurnTimer();
  currentIndex.value = idx; const p = pages.value[idx]; if (!p) return; loadingPage.value = true;
  try { const r = await $api.get(`/study-assignments/${assignId.value}/page/${encodeURIComponent(p.file)}`); pageHtmlContent.value = r.data.data.html; pageTextContent.value = r.data.data.text || ""; } catch { pageHtmlContent.value = ""; pageTextContent.value = ""; } finally { loadingPage.value = false; }
  nextTick(() => { resetTurnTimer(); startAudio(); });
}

function prevPage() { if (currentIndex.value > 0) { reportProgress(); loadPage(currentIndex.value - 1); } }
function nextPage() { if (currentIndex.value < pages.value.length - 1) { reportProgress(); loadPage(currentIndex.value + 1); } }

async function doComplete() {
  clearTurnTimer(); clearInterval(timer); clearInterval(progressTimer);
  try { await $api.post(`/study-assignments/${assignId.value}/complete`, { seconds: sessionSeconds.value }); isCompleted.value = true; state.value = "done"; } catch {}
}

watch(reading, (val) => { if (val) startAudio(); else if (audioEl.value) { audioEl.value.pause(); audioEl.value.src = ""; } });
watch(autoTurn, (val) => { if (!val) clearTurnTimer(); else resetTurnTimer(); });

onUnmounted(() => { clearTurnTimer(); clearInterval(timer); clearInterval(progressTimer); reportProgress(); if (audioEl.value) audioEl.value.pause(); });
onMounted(fetchInfo);
</script>
