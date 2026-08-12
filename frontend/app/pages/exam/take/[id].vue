<template>
  <div class="h-screen flex flex-col bg-gray-100" :class="{ 'select-none': !examDebug }" @contextmenu="blockCtx" @copy="blockCtx" @selectstart="blockCtx">
    <div v-if="state === 'start'" class="flex-1 flex items-center justify-center">
      <div v-if="loadError" class="text-gray-400 text-sm">加载失败，请关闭此窗口后重试。</div>
      <div v-else class="bg-white rounded-2xl shadow-xl p-8 max-w-md mx-4 text-center">
        <h1 class="text-2xl font-bold text-gray-900 mb-2">{{ exam?.name }}</h1>
        <p class="text-sm text-gray-500 mb-4">{{ exam?.description }}</p>
        <div class="text-sm text-gray-600 space-y-1 mb-6">
          <div>考试时长：{{ exam?.duration_minutes }} 分钟</div>
          <div>题目数量：{{ questions.length }} 题</div>
          <div>及格分数：{{ exam?.pass_score }} 分</div>
        </div>
        <button @click="start" class="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-lg font-bold">开始考试</button>
      </div>
    </div>

    <div v-else-if="state === 'exam'" class="flex-1 flex flex-col">
      <div class="flex-1 flex items-center justify-center p-8 overflow-auto">
        <div class="bg-white rounded-2xl shadow-lg p-8 max-w-2xl w-full">
          <div class="text-xs text-gray-400 mb-2">{{ typeLabel(currentQ.type) }}</div>
          <h2 class="text-lg font-bold text-gray-900 mb-4">{{ currentIndex + 1 }}. {{ currentQ.question }}</h2>

          <div v-if="currentQ.type === 'single'" class="space-y-2">
            <button v-for="(opt, i) in currentQ.options" :key="i" @click="setAnswer(currentQ.id, opt[0])" class="w-full text-left px-4 py-3 rounded-lg border text-sm" :class="answers[currentQ.id] === opt[0] ? 'border-primary-400 bg-primary-50' : 'border-gray-200 hover:bg-gray-50'">{{ opt }}</button>
          </div>
          <div v-else-if="currentQ.type === 'multiple'" class="space-y-2">
            <button v-for="(opt, i) in currentQ.options" :key="i" @click="toggleMulti(currentQ.id, opt[0])" class="w-full text-left px-4 py-3 rounded-lg border text-sm" :class="(answers[currentQ.id] || []).includes(opt[0]) ? 'border-primary-400 bg-primary-50' : 'border-gray-200 hover:bg-gray-50'">{{ opt }}</button>
          </div>
          <div v-else-if="currentQ.type === 'true_false'" class="flex gap-3">
            <button @click="setAnswer(currentQ.id, true)" class="flex-1 py-3 rounded-lg border text-sm" :class="answers[currentQ.id] === true ? 'border-primary-400 bg-primary-50' : 'border-gray-200 hover:bg-gray-50'">正确</button>
            <button @click="setAnswer(currentQ.id, false)" class="flex-1 py-3 rounded-lg border text-sm" :class="answers[currentQ.id] === false ? 'border-primary-400 bg-primary-50' : 'border-gray-200 hover:bg-gray-50'">错误</button>
          </div>
          <div v-else-if="currentQ.type === 'fill'" class="space-y-2">
            <textarea v-model="answers[currentQ.id]" rows="2" placeholder="请输入答案..." class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"></textarea>
          </div>
          <div v-else-if="currentQ.type === 'match'" class="space-y-2">
            <div v-for="left in currentQ.left" :key="left" class="flex items-center gap-2">
              <span class="text-sm font-medium w-20">{{ left }}</span>
              <select @change="setMatch(currentQ.id, left, $event.target.value)" class="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white">
                <option value="">请选择</option>
                <option v-for="r in currentQ.right" :key="r" :value="r">{{ r }}</option>
              </select>
            </div>
          </div>
        </div>
      </div>
      <div class="bg-white border-t border-gray-200 px-4 py-3 flex items-center justify-between">
        <button @click="prev" :disabled="currentIndex <= 0" class="px-4 py-2 border border-gray-200 rounded-lg text-sm disabled:opacity-40">&larr; 上一题</button>
        <div class="text-sm text-gray-500">
          {{ currentIndex + 1 }} / {{ questions.length }}
          <span class="ml-3 text-xs text-gray-400">剩余 {{ questions.length - currentIndex - 1 }} 题</span>
          <span class="ml-3 text-xs text-red-500">{{ formatTime(timeLeft) }}</span>
        </div>
        <button v-if="currentIndex < questions.length - 1" @click="next" class="px-4 py-2 border border-gray-200 rounded-lg text-sm">下一题 &rarr;</button>
        <button v-else @click="finish(false)" class="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm">结束考试</button>
      </div>
    </div>

    <div v-else-if="state === 'review'" class="flex-1 flex items-center justify-center p-8">
      <div class="bg-white rounded-2xl shadow-xl p-8 max-w-md mx-4 text-center">
        <div class="text-xs text-gray-500 mb-2">答题完成</div>
        <div class="text-lg font-bold text-gray-900 mb-2">完成题数：{{ answeredCount }}</div>
        <div class="text-sm text-gray-500 mb-4">总题数：{{ questions.length }}</div>
        <button @click="finish(true)" class="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-bold">提交并结束考试</button>
      </div>
    </div>

    <div v-else-if="state === 'done'" class="flex-1 flex items-center justify-center p-8">
      <div class="bg-white rounded-2xl shadow-xl p-8 max-w-md mx-4 text-center">
        <h2 class="text-xl font-bold text-gray-900 mb-4">考试已完成</h2>
        <div v-if="result" class="space-y-2 text-sm mb-6">
          <div>正确：{{ result.correct }} / {{ result.total }}</div>
          <div class="text-2xl font-bold" :class="result.passed ? 'text-green-600' : 'text-red-500'">{{ result.score }} 分</div>
          <div>{{ result.passed ? '通过' : '未通过' }}</div>
          <div v-if="result.evaluation" class="text-xs text-gray-500 mt-2">{{ result.evaluation }}</div>
        </div>
        <button @click="closeWindow" class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">关闭窗口</button>
      </div>
    </div>
    <div v-if="submitting" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/60">
      <div class="bg-white rounded-2xl shadow-xl px-8 py-6 text-center">
        <div class="inline-block w-8 h-8 border-4 border-primary-400 border-t-transparent rounded-full animate-spin mb-4"></div>
        <p class="text-sm text-gray-700 font-medium">正在提交并评分，请稍候...</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";

definePageMeta({ layout: false });

const { $api } = useNuxtApp();
const route = useRoute();
const runtime = useRuntimeConfig();
const examDebug = runtime.public.examDebug === "true";

const state = ref("start"); const exam = ref(null); const questions = ref([]);
const currentIndex = ref(0); const answers = ref({}); const timeLeft = ref(0); const result = ref(null);
const loadError = ref(false);
const submitting = ref(false);
const answeredCount = computed(() => Object.keys(answers.value).length);
const currentQ = computed(() => questions.value[currentIndex.value]);
let timer;

function typeLabel(t) { const m = { single: "单选", multiple: "多选", true_false: "对错", fill: "填空", match: "匹配" }; return m[t] || t; }
function formatTime(sec) { const m = Math.floor(sec/60); const s = sec%60; return `${m}:${String(s).padStart(2,'0')}`; }

async function fetchExam() {
  loadError.value = false;
  try { const r = await $api.get(`/exams/${route.params.id}/take`); exam.value = r.data.data; questions.value = r.data.data.questions; timeLeft.value = (r.data.data.duration_minutes || 30) * 60; } catch { loadError.value = true; }
}

function start() { state.value = "exam"; timer = setInterval(() => { timeLeft.value--; if (timeLeft.value <= 0) { clearInterval(timer); doSubmit(); } }, 1000); }

function setAnswer(qid, val) { answers.value[qid] = val; }
function toggleMulti(qid, opt) { const cur = answers.value[qid] || []; if (cur.includes(opt)) { answers.value[qid] = cur.filter(c => c !== opt); } else { answers.value[qid] = [...cur, opt]; } }
function setMatch(qid, left, right) { const cur = answers.value[qid] || {}; cur[left] = right; answers.value[qid] = { ...cur }; }

function prev() { if (currentIndex.value > 0) currentIndex.value--; }
function next() { if (currentIndex.value < questions.value.length - 1) currentIndex.value++; }
function finish(confirmed) { if (!confirmed) { state.value = "review"; } else { doSubmit(); } }

async function doSubmit() {
  clearInterval(timer);
  submitting.value = true;
  const ansList = Object.entries(answers.value).map(([qid, answer]) => ({ question_id: qid, answer }));
  try {
    const r = await $api.post(`/exams/${route.params.id}/submit`, { answers: ansList });
    result.value = r.data.data; state.value = "done";
  } catch { state.value = "done"; result.value = { correct: 0, total: questions.value.length, score: 0, passed: false, evaluation: "" }; } finally { submitting.value = false; }
}

function closeWindow() { try { window.close(); } catch {} }
function blockCtx(e) { if (!examDebug) e.preventDefault(); }

onUnmounted(() => { clearInterval(timer); });
onMounted(fetchExam);
</script>
