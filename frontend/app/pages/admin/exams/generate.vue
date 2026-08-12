<template>
  <div>
    <div class="mb-4"><NuxtLink to="/admin/exams" class="text-sm text-primary-600 hover:underline">&larr; 返回试卷列表</NuxtLink></div>
    <h2 class="text-xl font-bold text-gray-900 mb-6">生成试卷</h2>

    <!-- Step indicator -->
    <div class="flex items-center gap-2 mb-6">
      <div v-for="(s, i) in steps" :key="i" class="flex items-center gap-2">
        <span class="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold" :class="step === i ? 'bg-primary-600 text-white' : step > i ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-400'">{{ step > i ? '✓' : i + 1 }}</span>
        <span class="text-sm" :class="step >= i ? 'text-gray-900' : 'text-gray-400'">{{ s }}</span>
        <span v-if="i < steps.length - 1" class="text-gray-300 mx-1">&rarr;</span>
      </div>
    </div>

    <!-- Step 1: Basic info -->
    <div v-if="step === 0" class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 max-w-lg">
      <div class="space-y-4">
        <div><label class="block text-sm font-medium text-gray-700 mb-1">名称 <span class="text-red-500">*</span></label><input v-model="info.name" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" /></div>
        <div><label class="block text-sm font-medium text-gray-700 mb-1">描述</label><textarea v-model="info.description" rows="2" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"></textarea></div>
        <div class="grid grid-cols-2 gap-3"><div><label class="block text-xs text-gray-500 mb-1">及格分数</label><input v-model.number="info.pass_score" type="number" min="1" max="100" class="w-32 px-3 py-2 text-sm border border-gray-200 rounded-lg" /></div></div>
      </div>
      <div class="flex gap-2 mt-6"><button @click="step = 1" :disabled="!info.name.trim()" class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50">下一步：选择题库</button></div>
    </div>

    <!-- Step 2: Select banks -->
    <div v-if="step === 1" class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div class="text-sm text-gray-700 mb-2 font-medium">各题库题目占比（%）——该题库题目占试卷总题数的百分比</div>
      <div v-if="bankLoading" class="text-sm text-gray-400 py-4">加载题库中...</div>
      <div v-else class="space-y-2 max-h-80 overflow-y-auto">
        <div v-for="b in bankList" :key="b.id" class="flex items-center gap-3 p-3 border border-gray-100 rounded-lg">
          <input type="checkbox" :checked="hasBank(b.id)" @change="toggleBank(b.id)" class="rounded" />
          <div class="flex-1">
            <span class="text-sm font-medium text-gray-900">{{ b.name }}</span>
            <div class="flex gap-2 mt-1 text-xs text-gray-400">
              <span v-for="(cnt, tp) in bankTypeCounts[b.id]" :key="tp">{{ typeLabel(tp) }}:{{ cnt }}</span>
            </div>
          </div>
          <input v-if="hasBank(b.id)" v-model.number="bankPcts[b.id]" type="number" min="0" max="100" class="w-16 px-2 py-1 text-sm border border-gray-200 rounded-lg" placeholder="自动" /><span v-if="hasBank(b.id)" class="text-sm text-gray-500">%</span>
        </div>
      </div>
      <div v-if="selectedBanks.length" class="text-sm mt-2">占比总和：<span :class="selectedBanks.length === 1 ? 'text-green-600' : (pctSum === 100 ? 'text-green-600' : pctSum > 100 ? 'text-red-500' : 'text-amber-600')">{{ selectedBanks.length === 1 ? 100 : pctSum }}%</span><span v-if="selectedBanks.length === 1" class="text-xs text-gray-400 ml-1">（单选时始终 100%）</span></div>
      <div class="flex gap-2 mt-4"><button @click="step = 0" class="px-4 py-2 border border-gray-200 text-sm rounded-lg">上一步</button><button @click="goStep2" :disabled="!selectedBanks.length" class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50">下一步：选择题型</button></div>
    </div>

    <!-- Step 3: Select types -->
    <div v-if="step === 2" class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 max-w-lg">
      <div class="space-y-3">
        <div v-for="tp in allTypes" :key="tp.value" class="flex items-center gap-3 p-3 border border-gray-100 rounded-lg">
          <input type="checkbox" :checked="hasType(tp.value)" @change="toggleType(tp.value)" class="rounded" />
          <span class="flex-1 text-sm font-medium text-gray-900">{{ tp.label }}</span>
          <div class="flex gap-2 items-center">
            <label class="text-xs text-gray-400">题数</label>
            <input v-if="hasType(tp.value)" v-model.number="typeCounts[tp.value]" type="number" min="1" class="w-16 px-2 py-1 text-sm border border-gray-200 rounded-lg" />
          </div>
          <div class="flex gap-2 items-center ml-2">
            <label class="text-xs text-gray-400">每题分</label>
            <input v-if="hasType(tp.value)" v-model.number="typeScores[tp.value]" type="number" min="1" class="w-16 px-2 py-1 text-sm border border-gray-200 rounded-lg" />
          </div>
        </div>
      </div>
      <div class="text-sm text-gray-500 mt-4">总分：<span :class="totalScore === 100 ? 'text-green-600 font-bold' : 'text-red-500 font-bold'">{{ totalScore }} / 100</span>，总题数：{{ totalCount }}</div>
      <div class="mt-3 p-3 bg-gray-50 rounded-lg flex items-center gap-3"><label class="text-xs text-gray-500">时长</label><input v-model.number="info.duration_minutes" @input="durationEdited = true" type="number" min="1" class="w-20 px-2 py-1.5 text-sm border border-gray-200 rounded-lg bg-white" /><span class="text-xs text-gray-400">分钟 · 建议 {{ estimatedDuration }} 分钟 · 可手动修改</span></div>
      <div class="flex gap-2 mt-4"><button @click="step = 1" class="px-4 py-2 border border-gray-200 text-sm rounded-lg">上一步</button><button @click="goValidate" :disabled="!selectedTypes.length || totalScore !== 100" class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50">下一步：生成预览</button></div>
    </div>

    <!-- Step 4: Validate + Generate -->
    <div v-if="step === 3" class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div v-if="validating" class="text-center text-gray-400 text-sm py-8">正在校验...</div>
      <div v-else-if="validateResult">
        <div v-if="!validateResult.valid" class="mb-4">
          <div class="text-red-600 font-bold mb-2">校验失败</div>
          <div v-for="(e, i) in validateResult.errors" :key="i" class="text-sm text-red-500">{{ e }}</div>
        </div>
        <div v-else>
          <div class="text-sm text-gray-700 mb-4"><span class="font-bold">考试时间：</span>{{ info.duration_minutes }} 分钟，<span class="font-bold">及格分数：</span>{{ info.pass_score }} 分</div>
          <h4 class="text-sm font-bold text-gray-700 mb-2">题库×题型分布</h4>
          <table class="w-full text-xs border border-gray-200 rounded mb-4">
            <thead><tr class="bg-gray-50"><th class="px-2 py-1 text-left text-gray-600">题库</th><th v-for="t in selectedTypes" :key="t" class="px-2 py-1 text-gray-600">{{ typeLabel(t) }}</th><th class="px-2 py-1 text-gray-600">合计</th></tr></thead>
            <tbody>
              <tr v-for="r in validateResult.cross_table" :key="r.qb_id"><td class="px-2 py-1 font-medium">{{ r.qb_name }}</td><td v-for="c in r.cells" class="px-2 py-1 text-center">{{ c.count || '' }}</td><td class="px-2 py-1 text-center font-bold">{{ r.total }}</td></tr>
              <tr class="bg-gray-50 font-bold"><td class="px-2 py-1">合计</td><td v-for="t in selectedTypes" class="px-2 py-1 text-center">{{ typeCounts[t] }}</td><td class="px-2 py-1 text-center">{{ totalCount }}</td></tr>
            </tbody>
          </table>
          <h4 class="text-sm font-bold text-gray-700 mb-2">分值分布</h4>
          <table class="w-full text-xs border border-gray-200 rounded mb-6">
            <thead><tr class="bg-gray-50"><th class="px-2 py-1 text-gray-600"></th><th v-for="t in selectedTypes" :key="t" class="px-2 py-1 text-gray-600">{{ typeLabel(t) }}</th><th class="px-2 py-1 text-gray-600">合计</th></tr></thead>
            <tbody>
              <tr><td class="px-2 py-1">每题分</td><td v-for="t in selectedTypes" class="px-2 py-1 text-center">{{ typeScores[t] }}</td><td class="px-2 py-1 text-center">-</td></tr>
              <tr><td class="px-2 py-1">题数</td><td v-for="t in selectedTypes" class="px-2 py-1 text-center">{{ typeCounts[t] }}</td><td class="px-2 py-1 text-center font-bold">{{ totalCount }}</td></tr>
              <tr class="bg-gray-50 font-bold"><td class="px-2 py-1">总分</td><td v-for="t in selectedTypes" class="px-2 py-1 text-center">{{ typeScores[t] * typeCounts[t] }}</td><td class="px-2 py-1 text-center text-green-600">100</td></tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="flex gap-2 mt-4">
        <button @click="step = 2" class="px-4 py-2 border border-gray-200 text-sm rounded-lg">上一步</button>
        <button v-if="validateResult && validateResult.valid" @click="doGenerate" :disabled="generating" class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50">{{ generating ? '生成中...' : '生成试卷' }}</button>
      </div>
    </div>

    <div v-if="message" class="mt-4 px-4 py-3 rounded-xl text-sm" :class="msgClass">{{ message }}</div>

    <div v-if="generating" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/60">
      <div class="bg-white rounded-2xl shadow-xl px-8 py-6 text-center">
        <div class="inline-block w-8 h-8 border-4 border-primary-400 border-t-transparent rounded-full animate-spin mb-4"></div>
        <p class="text-sm text-gray-700 font-medium">正在生成试卷，请稍候...</p>
      </div>
    </div>

    <div v-if="leaveConfirmOpen" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/60">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm mx-4 p-6 text-center">
        <div class="text-2xl mb-3">&#x26A0;&#xFE0F;</div>
        <h3 class="text-lg font-bold text-gray-900 mb-2">有未保存的内容</h3>
        <p class="text-sm text-gray-500 mb-4">离开后已填写的内容将丢失。</p>
        <div class="flex gap-3">
          <button @click="confirmLeave" class="flex-1 py-2 bg-red-500 text-white text-sm rounded-lg hover:bg-red-600">离开</button>
          <button @click="cancelLeave" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50">继续编辑</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { onBeforeRouteLeave } from "vue-router";
definePageMeta({ middleware: ["auth", "teacher"] });
const { $api } = useNuxtApp();
const router = useRouter();

const steps = ["基本信息", "选择题库", "选择题型", "校验与生成"];
const step = ref(0);

const info = ref({ name: "", description: "", duration_minutes: 30, pass_score: 60 });
const bankList = ref([]); const bankTypeCounts = ref({}); const bankLoading = ref(false);
const bankPcts = ref({}); const selectedBanks = computed(() => Object.keys(bankPcts.value).filter(k => bankPcts.value[k] !== undefined));
const pctSum = computed(() => selectedBanks.value.reduce((s, id) => s + (bankPcts.value[id] || 0), 0));
const allTypes = [{ value: "single", label: "单选" }, { value: "multiple", label: "多选" }, { value: "true_false", label: "对错" }, { value: "fill", label: "填空" }, { value: "match", label: "匹配" }];
const typeCounts = ref({ }); const typeScores = ref({ });
const selectedTypes = computed(() => Object.keys(typeCounts.value).filter(k => typeCounts.value[k] !== undefined));
const totalScore = computed(() => selectedTypes.value.reduce((s, t) => s + (typeScores.value[t] || 0) * (typeCounts.value[t] || 0), 0));
const totalCount = computed(() => selectedTypes.value.reduce((s, t) => s + (typeCounts.value[t] || 0), 0));

const durationEdited = ref(false);
const runtime = useRuntimeConfig();
const perTypeSeconds = {
  single: Number(runtime.public.examEstSingle) || 60,
  multiple: Number(runtime.public.examEstMultiple) || 80,
  true_false: Number(runtime.public.examEstTrueFalse) || 45,
  fill: Number(runtime.public.examEstFill) || 80,
  match: Number(runtime.public.examEstMatch) || 120,
};
const estimatedDuration = computed(() => {
  let secs = 0;
  for (const [t, c] of Object.entries(typeCounts.value)) {
    secs += (c || 0) * (perTypeSeconds[t] || 60);
  }
  return Math.ceil(secs / 60) || 1;
});
watch(totalCount, () => {
  if (!durationEdited.value) {
    info.value.duration_minutes = estimatedDuration.value;
  }
});

const validating = ref(false); const validateResult = ref(null);
const generating = ref(false); const saved = ref(false);
const leaveConfirmOpen = ref(false);
const message = ref(""); const msgType = ref("success");
const msgClass = computed(() => msgType.value === "success" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700");

function typeLabel(t) { const m = { single: "单选", multiple: "多选", true_false: "对错", fill: "填空", match: "匹配" }; return m[t] || t; }

function hasBank(id) { return bankPcts.value[id] !== undefined; }
function toggleBank(id) {
  if (hasBank(id)) { delete bankPcts.value[id]; } else { bankPcts.value[id] = 0; }
}

function hasType(t) { return typeCounts.value[t] !== undefined; }
function toggleType(t) {
  if (hasType(t)) { delete typeCounts.value[t]; delete typeScores.value[t]; } else { typeCounts.value[t] = 1; typeScores.value[t] = 5; }
}

async function loadBanks() {
  bankLoading.value = true;
  try {
    const r = await $api.get("/question-banks", { params: { page_size: 100 } });
    bankList.value = r.data.data.items.filter(b => !b.disabled);
    for (const b of bankList.value) {
      try {
        const p = await $api.get(`/question-banks/${b.id}/paper`);
        const qs = p.data.data.questions || [];
        const counts = {};
        for (const q of qs) counts[q.type] = (counts[q.type] || 0) + 1;
        bankTypeCounts.value[b.id] = counts;
      } catch { bankTypeCounts.value[b.id] = {}; }
    }
  } catch {} finally { bankLoading.value = false; }
}

function goStep2() {
  if (!selectedBanks.value.length) return;
  step.value = 2;
}

async function goValidate() {
  validating.value = true; step.value = 3; validateResult.value = null;
  try {
    const body = {
      name: info.value.name, description: info.value.description,
      duration_minutes: info.value.duration_minutes, pass_score: info.value.pass_score,
      banks: selectedBanks.value.map(id => ({ qb_id: parseInt(id), percentage: bankPcts.value[id] || 0 })),
      types: selectedTypes.value.map(t => ({ type: t, count: typeCounts.value[t], score: typeScores.value[t] })),
    };
    const r = await $api.post("/exams/generate/validate", body);
    validateResult.value = r.data.data;
  } catch (e) { showMessage(e.response?.data?.detail || "校验失败", "error"); } finally { validating.value = false; }
}

async function doGenerate() {
  generating.value = true;
  try {
    const body = {
      name: info.value.name, description: info.value.description,
      duration_minutes: info.value.duration_minutes, pass_score: info.value.pass_score,
      banks: selectedBanks.value.map(id => ({ qb_id: parseInt(id), percentage: bankPcts.value[id] || 0 })),
      types: selectedTypes.value.map(t => ({ type: t, count: typeCounts.value[t], score: typeScores.value[t] })),
    };
    await $api.post("/exams/generate", body);
    saved.value = true;
    showMessage("生成成功", "success");
    await router.push("/admin/exams");
  } catch (e) { showMessage(e.response?.data?.detail || "生成失败", "error"); } finally { generating.value = false; }
}

function showMessage(msg, type) { message.value = msg; msgType.value = type; setTimeout(() => { message.value = ""; }, 3000); }

const isDirty = computed(() => info.value.name.trim() || selectedBanks.value.length > 0 || selectedTypes.value.length > 0);
let pendingLeave = null;
onBeforeRouteLeave((_to, _from, next) => {
  if (isDirty.value && !saved.value && !generating.value) {
    pendingLeave = next;
    leaveConfirmOpen.value = true;
  } else {
    next();
  }
});
function confirmLeave() { leaveConfirmOpen.value = false; if (pendingLeave) { pendingLeave(); pendingLeave = null; } }
function cancelLeave() { leaveConfirmOpen.value = false; if (pendingLeave) { pendingLeave(false); pendingLeave = null; } }

loadBanks();
</script>
