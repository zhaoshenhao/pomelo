<template>
  <div>
    <div class="mb-4">
      <NuxtLink to="/admin/study-materials" class="text-sm text-primary-600 hover:underline">&larr; 返回学习资料列表</NuxtLink>
    </div>

    <div v-if="!material" class="text-center text-gray-400 py-20">加载中...</div>

    <div v-else>
      <div class="mb-6">
        <h2 class="text-xl font-bold text-gray-900">{{ material.name }}</h2>
        <p class="text-sm text-gray-500 mt-1">{{ material.description || '暂无描述' }}</p>
        <div class="flex flex-wrap items-center gap-3 mt-3 text-xs text-gray-400">
          <span>文档库：{{ material.library_name }}</span>
          <span>创建人：{{ material.creator_name }}</span>
          <span>创建日期：{{ formatDate(material.created_at) }}</span>
        </div>
      </div>

      <div v-if="material.pages.length === 0" class="text-center text-gray-400 py-12">暂无页面内容</div>

      <div v-else class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div class="px-4 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <button @click="prevPage" :disabled="currentIndex <= 0" class="px-3 py-1 text-xs border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed">&larr; 上一页</button>
            <span class="text-xs text-gray-500">{{ currentIndex + 1 }} / {{ material.pages.length }}</span>
            <button @click="nextPage" :disabled="currentIndex >= material.pages.length - 1" class="px-3 py-1 text-xs border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed">下一页 &rarr;</button>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-xs px-2 py-0.5 rounded-full" :class="pageTypeBadge(pageTypeLabel)">
              {{ pageTypeLabel }}
            </span>
            <span class="text-xs text-gray-500">{{ currentPage?.title }}</span>
          </div>
          <button @click="showNarration = !showNarration" class="px-3 py-1 text-xs border border-gray-200 rounded-lg hover:bg-gray-50">
            {{ showNarration ? '查看页面' : '朗读文本(.txt)' }}
          </button>
          <label class="flex items-center gap-1 text-xs text-gray-500 cursor-pointer select-none">
            <input type="checkbox" v-model="autoTurn" class="w-3.5 h-3.5 text-primary-600 rounded" />
            自动翻页
          </label>
          <label class="flex items-center gap-1 text-xs text-gray-500 cursor-pointer select-none">
            <input type="checkbox" v-model="reading" class="w-3.5 h-3.5 text-primary-600 rounded" />
            朗读
          </label>
        </div>

        <div class="flex" style="height: calc(100vh - 280px); min-height: 400px;">
          <div class="w-60 border-r border-gray-200 overflow-y-auto bg-gray-50 flex-shrink-0">
            <div v-for="(p, idx) in material.pages" :key="idx"
              @click="loadPage(idx)"
              class="px-3 py-2 text-xs border-b border-gray-100 cursor-pointer hover:bg-white transition"
              :class="idx === currentIndex ? 'bg-white text-primary-700 font-medium border-l-2 border-l-primary-600' : 'text-gray-600'">
              <span class="text-[10px] text-gray-400 mr-1">{{ pageTypeShort(p.type) }}</span>
              {{ p.title || (p.type === 'cover' ? '封面' : p.type === 'end' ? '结束' : `第${p.chapter}章`) }}
            </div>
          </div>
          <div class="flex-1 overflow-auto">
            <div v-if="loadingPage" class="flex items-center justify-center h-full text-gray-400 text-sm">加载中...</div>
            <div v-else-if="showNarration" class="whitespace-pre-wrap p-8 text-sm text-gray-700 leading-relaxed font-sans">{{ pageTextContent || '(无朗读文本)' }}</div>
            <div v-else class="h-full">
              <iframe v-if="pageHtmlContent" :srcdoc="pageHtmlContent" class="w-full h-full border-0" sandbox="allow-same-origin"></iframe>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="message" class="mt-4 px-4 py-3 rounded-xl text-sm" :class="msgClass">{{ message }}</div>
    <audio ref="audioEl" class="hidden"></audio>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted, nextTick, watch } from "vue";

definePageMeta({ middleware: ["auth", "teacher"] });

const { $api } = useNuxtApp();
const route = useRoute();

const material = ref(null);
const currentIndex = ref(0);
const pageHtmlContent = ref("");
const pageTextContent = ref("");
const loadingPage = ref(false);
const showNarration = ref(false);
const message = ref("");
const msgType = ref("success");
const autoTurn = ref(true);
const reading = ref(false);
const audioEl = ref(null);
let turnTimer = null;

const msgClass = computed(() => msgType.value === "success" ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200");

const currentPage = computed(() => material.value?.pages?.[currentIndex.value]);
const pageTypeLabel = computed(() => {
  const t = currentPage.value?.type;
  const map = { cover: "封面", chapter_cover: "章节封面", page: "内容页", end: "结束页" };
  return map[t] || t;
});

function formatDate(d) {
  if (!d) return "";
  return d.substring(0, 16).replace("T", " ");
}

function pageTypeBadge(t) {
  const map = { "封面": "bg-blue-50 text-blue-700 border-blue-200", "章节封面": "bg-purple-50 text-purple-700 border-purple-200", "内容页": "bg-amber-50 text-amber-700 border-amber-200", "结束页": "bg-green-50 text-green-700 border-green-200" };
  return map[t] || "bg-gray-50 text-gray-600 border-gray-200";
}

function pageTypeShort(t) {
  const map = { cover: "封面", chapter_cover: "章封面", page: "页", end: "结束" };
  return map[t] || t;
}

async function fetchDetail() {
  try {
    const res = await $api.get(`/study-materials/${route.params.id}`);
    material.value = res.data.data;
    if (material.value.pages.length > 0) {
      loadPage(0);
    }
  } catch (e) {
    showMessage("加载失败", "error");
  }
}

function estimateDuration(text) {
  if (!text) return 5;
  return Math.max(2, text.length / 4.5);
}

function clearTurnTimer() {
  if (turnTimer) { clearTimeout(turnTimer); turnTimer = null; }
}

function resetTurnTimer() {
  clearTurnTimer();
  if (!autoTurn.value) return;
  const page = currentPage.value;
  const dur = page?.audio_duration || estimateDuration(pageTextContent.value);
  turnTimer = setTimeout(() => {
    if (currentIndex.value >= material.value.pages.length - 1) {
      loadPage(0);
    } else {
      loadPage(currentIndex.value + 1);
    }
  }, (dur + 0.3) * 1000);
}

function startAudio() {
  if (!reading.value) return;
  const page = currentPage.value;
  if (!page?.audio_file) return;
  const ad = audioEl.value;
  if (ad) { ad.pause(); ad.src = ""; }
  $api.get(`/study-materials/${route.params.id}/audio/${encodeURIComponent(page.audio_file)}`, { responseType: "blob" }).then((res) => {
    if (reading.value && currentPage.value?.audio_file === page.audio_file && audioEl.value) {
      const url = URL.createObjectURL(res.data);
      audioEl.value.src = url;
      audioEl.value.play().catch(() => {});
    }
  });
}

async function loadPage(idx) {
  clearTurnTimer();
  currentIndex.value = idx;
  const page = material.value.pages[idx];
  if (!page) return;
  loadingPage.value = true;
  try {
    const res = await $api.get(`/study-materials/${route.params.id}/page/${encodeURIComponent(page.file)}`);
    pageHtmlContent.value = res.data.data.html;
    pageTextContent.value = res.data.data.text;
  } catch {
    pageHtmlContent.value = "";
    pageTextContent.value = "";
  } finally {
    loadingPage.value = false;
  }
  nextTick(() => { resetTurnTimer(); startAudio(); });
}

onUnmounted(() => { clearTurnTimer(); if (audioEl.value) { audioEl.value.pause(); } });

watch(reading, (val) => {
  if (val) { startAudio(); }
  else if (audioEl.value) { audioEl.value.pause(); audioEl.value.src = ""; }
});

function prevPage() {
  if (currentIndex.value > 0) loadPage(currentIndex.value - 1);
}

function nextPage() {
  if (currentIndex.value < material.value.pages.length - 1) loadPage(currentIndex.value + 1);
}

function showMessage(msg, type) {
  message.value = msg;
  msgType.value = type;
  setTimeout(() => { message.value = ""; }, 3000);
}

fetchDetail();
</script>
