<template>
  <div class="h-screen flex flex-col bg-gray-100">
    <div v-if="state === 'start'" class="flex-1 flex items-center justify-center">
      <div v-if="loadError" class="text-gray-400 text-sm">加载失败，请关闭此窗口后重试。</div>
      <div v-else class="bg-white rounded-2xl shadow-xl p-8 max-w-md mx-4 text-center">
        <h1 class="text-2xl font-bold text-gray-900 mb-2">{{ bankName }}</h1>
        <div class="text-sm text-gray-600 space-y-1 mb-6">
          <div>训练模式：无时间限制</div>
          <div>每题答完立即反馈</div>
          <div>题目数量：{{ questions.length }} 题</div>
        </div>
        <button @click="startTraining" class="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-lg font-bold">开始训练</button>
      </div>
    </div>

    <div v-else-if="state === 'training'" class="flex-1 flex flex-col">
      <div class="flex-1 flex items-center justify-center p-8 overflow-auto">
        <div class="bg-white rounded-2xl shadow-lg p-8 max-w-2xl w-full">
          <div class="text-xs text-gray-400 mb-2">{{ typeLabel(currentQ.type) }}</div>
          <h2 class="text-lg font-bold text-gray-900 mb-4">{{ currentIndex + 1 }}. {{ currentQ.question }}</h2>

          <div v-if="currentQ.type === 'single'" class="space-y-2">
            <button v-for="(opt, i) in currentQ.options" :key="i" @click="answers[currentQ.id] = opt[0]" class="w-full text-left px-4 py-3 rounded-lg border text-sm" :class="answers[currentQ.id] === opt[0] ? 'border-primary-400 bg-primary-50' : 'border-gray-200 hover:bg-gray-50'">{{ opt }}</button>
          </div>
          <div v-else-if="currentQ.type === 'multiple'" class="space-y-2">
            <button v-for="(opt, i) in currentQ.options" :key="i" @click="toggleMulti(currentQ.id, opt[0])" class="w-full text-left px-4 py-3 rounded-lg border text-sm" :class="(answers[currentQ.id] || []).includes(opt[0]) ? 'border-primary-400 bg-primary-50' : 'border-gray-200 hover:bg-gray-50'">{{ opt }}</button>
          </div>
          <div v-else-if="currentQ.type === 'true_false'" class="flex gap-3">
            <button @click="answers[currentQ.id] = true" class="flex-1 py-3 rounded-lg border text-sm" :class="answers[currentQ.id] === true ? 'border-primary-400 bg-primary-50' : 'border-gray-200 hover:bg-gray-50'">正确</button>
            <button @click="answers[currentQ.id] = false" class="flex-1 py-3 rounded-lg border text-sm" :class="answers[currentQ.id] === false ? 'border-primary-400 bg-primary-50' : 'border-gray-200 hover:bg-gray-50'">错误</button>
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
        <button @click="stopTraining" class="px-4 py-2 border border-red-200 text-red-500 rounded-lg text-sm hover:bg-red-50">停止训练</button>
        <div class="text-sm text-gray-500">
          {{ currentIndex + 1 }} / {{ questions.length }}
          <span class="ml-3 text-xs text-gray-400">{{ formatTime(elapsed) }}</span>
        </div>
        <button @click="goNext" :disabled="!hasCurrentAnswer || submitting" class="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm disabled:opacity-50 hover:bg-primary-700">{{ currentIndex < questions.length - 1 ? '下一题' : '完成本题' }}</button>
      </div>
    </div>

    <div v-if="wrongModal.show" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 p-6">
        <div class="text-center mb-4">
          <div class="text-2xl mb-2">&#x274C;</div>
          <h3 class="text-lg font-bold text-red-500">回答错误</h3>
        </div>
        <div class="text-sm text-gray-700 bg-gray-50 rounded-lg p-3 mb-2">
          <span class="text-xs text-gray-400">正确答案：</span>
          <div class="font-medium mt-1">{{ wrongModal.correctAnswer }}</div>
        </div>
        <div v-if="wrongModal.explanation" class="text-sm text-gray-600 bg-gray-50 rounded-lg p-3 mb-4">{{ wrongModal.explanation }}</div>
        <button @click="confirmWrong" class="w-full py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm">知道了，继续</button>
      </div>
    </div>

    <div v-if="roundSummary.show" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm mx-4 p-6 text-center">
        <h3 class="text-lg font-bold text-gray-900 mb-4">本轮完成</h3>
        <div class="text-4xl font-bold mb-2" :class="roundSummary.correct === roundSummary.total ? 'text-green-600' : 'text-primary-600'">{{ roundSummary.correct }} / {{ roundSummary.total }}</div>
        <p class="text-sm text-gray-500 mb-4">答对 {{ roundSummary.total ? Math.round(roundSummary.correct / roundSummary.total * 100) : 0 }}%</p>
        <div class="flex gap-3">
          <button @click="nextRound" class="flex-1 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700">继续训练</button>
          <button @click="closeWindow" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50">结束训练</button>
        </div>
      </div>
    </div>

    <div v-if="stopConfirm.show" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm mx-4 p-6 text-center">
        <h3 class="text-lg font-bold text-gray-900 mb-2">停止训练？</h3>
        <p class="text-sm text-gray-500 mb-4">当前答题进度将保存，确定要停止吗？</p>
        <div class="flex gap-3">
          <button @click="confirmStop" class="flex-1 py-2 bg-red-500 text-white text-sm rounded-lg hover:bg-red-600">确定停止</button>
          <button @click="stopConfirm.show = false" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50">继续训练</button>
        </div>
      </div>
    </div>

    <div v-if="submitting" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/60">
      <div class="bg-white rounded-2xl shadow-xl px-8 py-6 text-center">
        <div class="inline-block w-8 h-8 border-4 border-primary-400 border-t-transparent rounded-full animate-spin mb-4"></div>
        <p class="text-sm text-gray-700 font-medium">提交中...</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";

definePageMeta({ layout: false });

const { $api } = useNuxtApp();
const route = useRoute();

const state = ref("start");
const loadError = ref(false);
const bankName = ref("");
const questions = ref([]);
const sessionId = ref("");
const currentIndex = ref(0);
const answers = ref({});
const elapsed = ref(0);
const submitting = ref(false);
const roundCorrect = ref(0);
const submittedThisRound = ref(new Set());

const wrongModal = ref({ show: false, correctAnswer: "", explanation: "" });
const roundSummary = ref({ show: false, correct: 0, total: 10 });
const stopConfirm = ref({ show: false });
let timer = null;

const currentQ = computed(() => questions.value[currentIndex.value] || {});
const hasCurrentAnswer = computed(() => {
  const qid = currentQ.value.id;
  if (!qid) return false;
  const a = answers.value[qid];
  if (a === undefined || a === null || a === "") return false;
  if (currentQ.value.type === "multiple" && (!Array.isArray(a) || a.length === 0)) return false;
  if (currentQ.value.type === "match") {
    const allLeft = currentQ.value.left || [];
    const hasAll = allLeft.every(l => a[l] && a[l] !== "");
    if (!hasAll) return false;
  }
  return true;
});

function typeLabel(t) { const m = { single: "单选", multiple: "多选", true_false: "对错", fill: "填空", match: "匹配" }; return m[t] || t; }
function formatTime(sec) { const m = Math.floor(sec / 60); const s = sec % 60; return `${m}:${String(s).padStart(2, "0")}`; }

function toggleMulti(qid, opt) {
  const cur = answers.value[qid] || [];
  if (cur.includes(opt)) { answers.value[qid] = cur.filter(c => c !== opt); } else { answers.value[qid] = [...cur, opt]; }
}
function setMatch(qid, left, right) {
  const cur = answers.value[qid] || {};
  cur[left] = right;
  answers.value[qid] = { ...cur };
}

async function startTraining() {
  state.value = "training";
  elapsed.value = 0;
  timer = setInterval(() => { elapsed.value++; }, 1000);
}

async function fetchSession() {
  loadError.value = false;
  try {
    const r = await $api.post("/drills/session/start", { qb_id: Number(route.params.qb_id) });
    const data = r.data.data;
    sessionId.value = data.session_id;
    questions.value = data.questions;
    bankName.value = data.qb_name || "";
  } catch { loadError.value = true; }
}

function answerValue(qid) {
  const a = answers.value[qid];
  if (a === undefined || a === null) return null;
  if (currentQ.value.type === "multiple") return Array.isArray(a) ? a : [];
  if (currentQ.value.type === "match") {
    if (typeof a !== "object") return {};
    return a;
  }
  return a;
}

function showAnswerText(ans, question) {
  if (!question) return String(ans);
  const t = question.type;
  if (t === "single") return `${ans}${question.options?.find(o => o.startsWith(ans))?.substring(1) || ""}`;
  if (t === "multiple") {
    const labels = (ans || []).map(a => question.options?.find(o => o.startsWith(a)) || a);
    return labels.join("、");
  }
  if (t === "true_false") return ans ? "正确" : "错误";
  if (t === "fill") return String(ans);
  if (t === "match") return typeof ans === "object" ? JSON.stringify(ans) : String(ans);
  return String(ans);
}

async function goNext() {
  if (!hasCurrentAnswer.value || submitting.value) return;
  const qid = currentQ.value.id;
  const ans = answerValue(qid);
  if (submittedThisRound.value.has(qid)) {
    advanceQuestion();
    return;
  }

  submitting.value = true;
  try {
    const r = await $api.post("/drills/answer", {
      session_id: sessionId.value,
      question_id: qid,
      answer: ans,
    });
    const res = r.data.data;
    if (!submittedThisRound.value.has(qid)) {
      submittedThisRound.value.add(qid);
      if (res.correct) roundCorrect.value++;
    }
    if (!res.correct) {
      wrongModal.value = {
        show: true,
        correctAnswer: showAnswerText(res.correct_answer, currentQ.value),
        explanation: res.explanation || "",
      };
    } else {
      advanceQuestion();
    }
  } catch {
    wrongModal.value = { show: true, correctAnswer: "提交失败", explanation: "请重试" };
  } finally { submitting.value = false; }
}

function confirmWrong() {
  wrongModal.value = { show: false, correctAnswer: "", explanation: "" };
  advanceQuestion();
}

function advanceQuestion() {
  if (currentIndex.value < questions.value.length - 1) {
    currentIndex.value++;
  } else {
    roundSummary.value = {
      show: true,
      correct: roundCorrect.value,
      total: questions.value.length,
    };
  }
}

async function nextRound() {
  roundSummary.value = { show: false, correct: 0, total: 0 };
  roundCorrect.value = 0;
  submittedThisRound.value = new Set();
  currentIndex.value = 0;
  answers.value = {};
  submitting.value = true;
  try {
    const r = await $api.post("/drills/session/start", { qb_id: Number(route.params.qb_id) });
    const data = r.data.data;
    sessionId.value = data.session_id;
    questions.value = data.questions;
    state.value = "training";
  } catch {} finally { submitting.value = false; }
}

function stopTraining() {
  stopConfirm.value = { show: true };
}

async function confirmStop() {
  stopConfirm.value = { show: false };
  if (hasCurrentAnswer.value && !submittedThisRound.value.has(currentQ.value.id)) {
    submitting.value = true;
    try {
      await $api.post("/drills/answer", {
        session_id: sessionId.value,
        question_id: currentQ.value.id,
        answer: answerValue(currentQ.value.id),
      });
    } catch {} finally { submitting.value = false; }
  }
  closeWindow();
}

async function submitPending() {
  if (!hasCurrentAnswer.value || !sessionId.value) return;
  if (submittedThisRound.value.has(currentQ.value.id)) return;
  const payload = JSON.stringify({
    session_id: sessionId.value,
    question_id: currentQ.value.id,
    answer: answerValue(currentQ.value.id),
  });
  if (navigator.sendBeacon) {
    const runtime = useRuntimeConfig();
    const apiBase = runtime.public.apiBase || "http://localhost:8080/api";
    const blob = new Blob([payload], { type: "application/json" });
    navigator.sendBeacon(`${apiBase}/drills/answer`, blob);
  }
}

function closeWindow() { clearInterval(timer); try { window.close(); } catch {} }

function blockCtx(e) { e.preventDefault(); }

onMounted(async () => {
  await fetchSession();
  window.addEventListener("beforeunload", (e) => {
    if (hasCurrentAnswer.value && !submittedThisRound.value.has(currentQ.value.id) && sessionId.value) {
      submitPending();
      e.preventDefault();
      e.returnValue = "";
    }
  });
});

onUnmounted(() => { clearInterval(timer); });
</script>
