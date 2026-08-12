<template>
  <div>
    <div class="mb-4"><NuxtLink to="/admin/exams" class="text-sm text-primary-600 hover:underline">&larr; 返回试卷列表</NuxtLink></div>
    <div v-if="!exam" class="text-center text-gray-400 py-20">加载中...</div>
    <div v-else>
      <div class="mb-6 flex items-center justify-between">
        <div><h2 class="text-xl font-bold text-gray-900">{{ exam.name }} - 成绩汇总</h2><p class="text-sm text-gray-500 mt-1">{{ exam.description || '暂无描述' }}</p></div>
        <div class="flex gap-2"><button v-if="activeBatch" @click="switchBatch(null)" class="text-xs px-3 py-1.5 border border-gray-200 rounded-lg hover:bg-gray-50">全部批次</button><button @click="confirmRegen = true" class="px-4 py-2 bg-accent-600 text-white text-sm rounded-lg hover:bg-accent-700">重新汇总</button><button @click="exportPdf" class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700">导出报表</button></div>
      </div>

      <div class="mb-4 flex flex-wrap gap-2">
        <button v-for="b in batches" :key="b.id" @click="switchBatch(b.id)" class="text-xs px-3 py-1.5 rounded-lg border" :class="activeBatch === b.id ? 'bg-primary-600 text-white border-primary-600' : 'border-gray-200 hover:bg-gray-50'">{{ b.name || '批次 #'+b.id }}</button>
      </div>

      <div v-if="summary" class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-white rounded-xl shadow-sm border p-4 text-center"><div class="text-2xl font-bold text-gray-900">{{ summary.total_students }}</div><div class="text-xs text-gray-500 mt-1">总人数</div></div>
        <div class="bg-white rounded-xl shadow-sm border p-4 text-center"><div class="text-2xl font-bold text-primary-600">{{ summary.average_score }}</div><div class="text-xs text-gray-500 mt-1">平均分</div></div>
        <div class="bg-white rounded-xl shadow-sm border p-4 text-center"><div class="text-2xl font-bold" :class="summary.pass_rate >= 60 ? 'text-green-600' : 'text-red-500'">{{ summary.pass_rate }}%</div><div class="text-xs text-gray-500 mt-1">及格率</div></div>
        <div class="bg-white rounded-xl shadow-sm border p-4 text-center"><div class="text-2xl font-bold text-gray-600">{{ students.length }}</div><div class="text-xs text-gray-500 mt-1">完成人数</div></div>
      </div>

      <div v-if="summary && summary.knowledge_coverage" class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-6"><h3 class="text-sm font-bold text-gray-700 mb-2">知识覆盖率分析</h3><p class="text-xs text-gray-500">{{ summary.knowledge_coverage }}</p></div>

      <div v-if="summary && summary.per_question_accuracy && summary.per_question_accuracy.length" class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-6">
        <h3 class="text-sm font-bold text-gray-700 mb-3">每题正确率</h3>
        <div class="space-y-2"><div v-for="q in summary.per_question_accuracy" :key="q.question_id" class="flex items-center gap-3"><span class="text-xs text-gray-500 w-10 cursor-pointer hover:text-primary-600 hover:underline" @click="showQuestion(q)">Q{{ q.question_id }}</span><div class="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden"><div class="h-full rounded-full text-xs text-white flex items-center px-2" :class="q.accuracy >= 60 ? 'bg-green-500' : 'bg-red-400'" :style="{ width: q.accuracy + '%' }">{{ q.accuracy }}%</div></div><span class="text-xs text-gray-400">{{ q.correct }}/{{ q.total_answers }}</span></div></div>
      </div>

      <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden mb-4">
        <table class="w-full text-sm"><thead class="bg-gray-50 text-left text-gray-600"><tr><th class="px-4 py-2">学员</th><th class="px-4 py-2">得分</th><th class="px-4 py-2">正确/总数</th><th class="px-4 py-2">状态</th><th class="px-4 py-2">操作</th></tr></thead>
          <tbody class="divide-y divide-gray-100"><tr v-for="s in students" :key="s.student_id" class="hover:bg-gray-50"><td class="px-4 py-2 text-gray-700">{{ s.student_name }}</td><td class="px-4 py-2 font-bold text-primary-600">{{ s.score }}</td><td class="px-4 py-2 text-gray-500">{{ s.correct }}/{{ s.total }}</td><td class="px-4 py-2"><span class="text-xs px-2 py-0.5 rounded-full" :class="s.passed ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-500'">{{ s.passed ? '通过' : '未通过' }}</span></td><td class="px-4 py-2"><button @click="viewStudent(s.student_id, s.batch_id)" class="text-xs text-primary-600 hover:underline">查看答卷</button></td></tr></tbody>
        </table>
      </div>
    </div>

    <div v-if="studentDetail" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="studentDetail = null">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-2xl mx-4 p-6 max-h-[85vh] overflow-y-auto">
        <h3 class="text-lg font-bold text-gray-900 mb-4">学员答卷 - {{ studentDetail.student_name || '' }}</h3>
        <div class="text-sm space-y-1 mb-4"><span class="text-green-600 font-bold">得分：{{ studentDetail.score }} / {{ studentDetail.total }}</span><span class="ml-4" :class="studentDetail.passed ? 'text-green-600' : 'text-red-500'">{{ studentDetail.passed ? '通过' : '未通过' }}</span></div>
        <div class="space-y-3"><div v-for="r in studentDetail.results" :key="r.question_id" class="border border-gray-100 rounded-lg p-3" :class="r.correct ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'"><div class="flex items-center gap-2 mb-1"><span class="text-xs font-bold text-gray-700">{{ r.question_id }}</span><span class="text-xs px-2 py-0.5 rounded-full" :class="r.correct ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-500'">{{ r.correct ? '正确' : '错误' }}</span></div><div class="text-sm text-gray-800 mb-2">{{ r.question }}</div><div class="text-xs text-gray-500">学员答：{{ formatVal(r.actual) }}　|　正确答案：{{ formatVal(r.expected) }}</div></div></div>
        <div v-if="studentDetail.evaluation" class="mt-4 bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-700">{{ studentDetail.evaluation }}</div>
        <div class="flex gap-2 mt-4"><button @click="studentDetail = null" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg">关闭</button></div>
      </div>
    </div>

    <div v-if="questionModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="questionModal = null">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-2xl mx-4 p-6 max-h-[85vh] overflow-y-auto">
        <h3 class="text-lg font-bold text-gray-900 mb-2">{{ questionModal.question_id }} · {{ typeLabel(questionModal.type) }}</h3>
        <div class="text-sm text-gray-800 mb-4" v-html="questionModal.question"></div>
        <div v-if="questionModal.type === 'single' || questionModal.type === 'multiple'" class="mb-4">
          <h4 class="text-xs font-bold text-gray-500 mb-1">选项</h4>
          <div v-for="opt in questionModal.options" :key="opt" class="text-xs py-1" :class="opt[0] === questionModal.answer || (questionModal.answers || []).includes(opt[0]) ? 'text-green-700 font-medium bg-green-50 -mx-1 px-1 rounded' : 'text-gray-600'">{{ opt }}</div>
        </div>
        <div v-else-if="questionModal.type === 'match'" class="mb-4">
          <h4 class="text-xs font-bold text-gray-500 mb-1">左项</h4><div class="text-xs text-gray-600 flex flex-wrap gap-2 mb-2"><span v-for="l in questionModal.left" :key="l" class="px-2 py-0.5 bg-gray-100 rounded">{{ l }}</span></div>
          <h4 class="text-xs font-bold text-gray-500 mb-1">右项</h4><div class="text-xs text-gray-600 flex flex-wrap gap-2 mb-2"><span v-for="r in questionModal.right" :key="r" class="px-2 py-0.5 bg-gray-100 rounded">{{ r }}</span></div>
        </div>
        <div class="border-t border-gray-100 pt-3 mb-3">
          <h4 class="text-xs font-bold text-gray-500 mb-1">正确答案</h4>
          <div class="text-sm font-medium text-green-700">{{ formatCorrectAnswer(questionModal) }}</div>
        </div>
        <div v-if="questionModal.explanation" class="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-3 text-xs text-amber-700">{{ questionModal.explanation }}</div>
        <button @click="questionModal = null" class="w-full py-2 border border-gray-200 text-sm rounded-lg">关闭</button>
      </div>
    </div>
    <ConfirmModal :show="confirmRegen" title="重新汇总" message="将重新扫描学员成绩并生成汇总。" variant="danger" @confirm="doRegen" @cancel="confirmRegen = false" />
    <div v-if="regenerating" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/60"><div class="bg-white rounded-2xl shadow-xl px-8 py-6 text-center"><div class="inline-block w-8 h-8 border-4 border-primary-400 border-t-transparent rounded-full animate-spin mb-4"></div><p class="text-sm text-gray-700 font-medium">正在重新汇总，请稍候...</p></div></div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
definePageMeta({ middleware: ["auth", "teacher"] });
const { $api } = useNuxtApp();
const route = useRoute();
const examId = computed(() => route.params.id);

const exam = ref(null); const summary = ref(null); const students = ref([]); const batches = ref([]);
const activeBatch = ref(null); const studentDetail = ref(null); const questionModal = ref(null); const confirmRegen = ref(false); const regenerating = ref(false);
const message = ref(""); const msgType = ref("success");
const msgClass = computed(() => msgType.value === "success" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700");
const paperMap = ref({});

function typeLabel(t) { const m = { single: "单选", multiple: "多选", true_false: "对错", fill: "填空", match: "匹配" }; return m[t] || t; }

function formatVal(v) { if (typeof v === 'object') return JSON.stringify(v); return v ?? '未答'; }

async function fetchAll() {
  try {
    exam.value = (await $api.get(`/exams/${examId.value}`)).data.data;
    const br = await $api.get(`/exams/${examId.value}/batches`);
    batches.value = br.data.data.batches || [];
  } catch {}
  await loadPaper();
  await loadResults();
}

async function loadPaper() {
  try {
    const pr = await $api.get(`/exams/${examId.value}/paper`);
    const qs = pr.data.data.questions || [];
    const m = {};
    for (const q of qs) m[q.id] = q;
    paperMap.value = m;
  } catch {}
}

function showQuestion(q) {
  const pq = paperMap.value[q.question_id];
  if (!pq) return;
  questionModal.value = {
    question_id: q.question_id,
    type: pq.type,
    question: pq.question,
    options: pq.options,
    left: pq.left,
    right: pq.right,
    answer: pq.answer,
    answers: pq.answers,
    matches: pq.matches,
    explanation: pq.explanation,
  };
}

function formatCorrectAnswer(pq) {
  if (pq.type === "single") return `${pq.answer}${pq.options?.find(o => o.startsWith(pq.answer))?.substring(1) || ""}`;
  if (pq.type === "multiple") return (pq.answers || []).map(a => `${a}${pq.options?.find(o => o.startsWith(a))?.substring(1) || ""}`).join("、");
  if (pq.type === "true_false") return pq.answer === true ? "正确" : "错误";
  if (pq.type === "fill") return pq.answer || "";
  if (pq.type === "match") return Object.entries(pq.matches || {}).map(([k, v]) => `${k} → ${v}`).join("；");
  return "";
}

async function loadResults() {
  try {
    let r;
    if (activeBatch.value) {
      r = await $api.get(`/exams/${examId.value}/batches/${activeBatch.value}/result`);
    } else {
      r = await $api.get(`/exams/${examId.value}/results`);
    }
    summary.value = r.data.data;
  } catch {}
  await loadStudents();
}

async function loadStudents() {
  try {
    const items = [];
    if (activeBatch.value) {
      const d = await $api.get(`/exams/${examId.value}/batches/${activeBatch.value}`);
      for (const a of d.data.data.students) {
        if (a.status === "completed") {
          items.push({ student_id: a.student_id, student_name: a.student_name, batch_id: a.batch_id, score: a.score || 0, correct: a.correct || 0, total: a.total || 0, passed: a.passed });
        }
      }
    } else {
      for (const b of batches.value) {
        try {
          const d = await $api.get(`/exams/${examId.value}/batches/${b.id}`);
          for (const a of d.data.data.students) {
            if (a.status === "completed") {
              items.push({ student_id: a.student_id, student_name: a.student_name, batch_id: a.batch_id, score: a.score || 0, correct: a.correct || 0, total: a.total || 0, passed: a.passed });
            }
          }
        } catch {}
      }
    }
    students.value = items;
  } catch {}
}

function switchBatch(bid) { activeBatch.value = bid; loadResults(); }

async function viewStudent(sid, bid) {
  try {
    const sr = await $api.get(`/exams/${examId.value}/batches/${bid}/students/${sid}`);
    const data = sr.data.data;
    const results = (data.results || []).map(r => ({ ...r, question: paperMap.value[r.question_id]?.question || r.question_id }));
    studentDetail.value = { ...data, results, student_name: students.value.find(s => s.student_id === sid)?.student_name || sid };
  } catch { showMessage("加载失败", "error"); }
}

async function doRegen() {
  confirmRegen.value = false; regenerating.value = true;
  try {
    if (activeBatch.value) {
      await $api.post(`/exams/${examId.value}/batches/${activeBatch.value}/result/regenerate`);
    } else {
      await $api.post(`/exams/${examId.value}/results/regenerate`);
    }
    showMessage("汇总完成", "success"); loadResults();
  } catch (e) { showMessage(e.response?.data?.detail || "汇总失败", "error"); } finally { regenerating.value = false; }
}

function showMessage(msg, type) { message.value = msg; msgType.value = type; setTimeout(() => { message.value = ""; }, 3000); }

async function exportPdf() {
  try {
    const params = activeBatch.value ? { batch_id: activeBatch.value } : {};
    const r = await $api.get(`/exams/${examId.value}/results/export`, { params, responseType: "blob" });
    const url = URL.createObjectURL(r.data);
    const a = document.createElement("a");
    a.href = url; a.download = `\u6210\u7ee9\u6c47\u603b-${exam.value?.name || examId.value}.html`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (e) { showMessage("导出失败", "error"); }
}
fetchAll();
</script>
