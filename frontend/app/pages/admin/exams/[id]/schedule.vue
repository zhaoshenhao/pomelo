<template>
  <div>
    <div class="mb-4"><NuxtLink to="/admin/exams" class="text-sm text-primary-600 hover:underline">&larr; 返回试卷列表</NuxtLink></div>
    <div v-if="!exam" class="text-center text-gray-400 py-20">加载中...</div>
    <div v-else>
      <div class="flex items-center justify-between mb-6">
        <div><h2 class="text-xl font-bold text-gray-900">{{ exam.name }} - 安排考试</h2><p class="text-sm text-gray-500 mt-1">{{ exam.description || '暂无描述' }}</p></div>
        <button @click="openCreate" class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700">+ 新建批次</button>
      </div>

      <div v-if="batches.length === 0" class="text-sm text-gray-400 mb-4">暂无批次</div>
      <div v-else class="space-y-3 mb-6">
        <div v-for="b in batches" :key="b.id" class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 flex items-center justify-between">
          <div>
            <span class="text-sm font-medium text-gray-900">{{ b.name || '批次 #'+b.id }}</span>
            <span class="text-xs text-gray-400 ml-3">安排人：{{ b.arranged_by_name }}</span>
            <span class="text-xs text-gray-400 ml-3">{{ formatDt(b.created_at) }}</span>
            <span class="text-xs ml-3" :class="b.disabled ? 'text-red-400' : 'text-green-600'">{{ b.disabled ? '已禁止' : '有效' }}</span>
            <div class="text-xs text-gray-500 mt-1">
              <span>已安排 {{ b.arranged_count || 0 }}</span>
              <span class="ml-2">已完成 {{ b.completed_count || 0 }}</span>
              <span class="ml-2" v-if="b.pass_rate !== null">及格率 {{ b.pass_rate }}%</span>
              <span class="ml-2" v-if="b.average_score !== null">平均分 {{ b.average_score }}</span>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <span class="text-xs text-gray-500">{{ b.start_time ? formatDt(b.start_time) : '-' }} ~ {{ b.end_time ? formatDt(b.end_time) : '-' }}</span>
            <button @click="openDetail(b)" class="text-xs text-primary-600 hover:underline">明细</button>
            <button @click="openEdit(b)" class="text-xs text-primary-600 hover:underline">编辑</button>
            <NuxtLink :to="`/admin/exams/${examId}/results?batch=${b.id}`" class="text-xs text-primary-600 hover:underline">成绩</NuxtLink>
            <button @click="handleDelete(b)" class="text-xs text-red-500 hover:underline">删除</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="panelOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="closePanel">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-3xl mx-4 p-6 max-h-[90vh] overflow-y-auto">
        <h3 class="text-lg font-bold text-gray-900 mb-4">{{ editingBatch ? '编辑批次' : '新建批次' }}</h3>
        <div class="space-y-3 text-sm">
          <div class="grid grid-cols-2 gap-3">
            <div><label class="block text-xs text-gray-500 mb-1">名称</label><input v-model="panel.name" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" /></div>
            <div><label class="block text-xs text-gray-500 mb-1">描述</label><input v-model="panel.description" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" /></div>
          </div>
          <div class="grid grid-cols-2 gap-3" v-if="!editingBatch">
            <div><label class="block text-xs text-gray-500 mb-1">开始时间</label><input type="datetime-local" v-model="panel.start_time" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" /></div>
            <div><label class="block text-xs text-gray-500 mb-1">结束时间</label><input type="datetime-local" v-model="panel.end_time" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" /></div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div><label class="block text-xs text-gray-500 mb-1">时长(分)</label><input v-model.number="panel.duration_minutes" type="number" min="1" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" /></div>
            <div><label class="block text-xs text-gray-500 mb-1">及格分</label><input v-model.number="panel.pass_score" type="number" min="1" max="100" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" /></div>
          </div>
          <div v-if="editingBatch"><label class="flex items-center gap-2"><input type="checkbox" v-model="panel.disabled" class="rounded" /><span class="text-sm text-gray-700">禁止（新建时不会出现此选项）</span></label></div>

          <div v-if="!editingBatch">
            <label class="block text-xs text-gray-500 mb-1">学员标签</label>
            <div class="flex flex-wrap gap-2">
              <label v-for="t in allTags" :key="t.id" class="flex items-center gap-1 text-xs"><input type="checkbox" :value="t.id" v-model="panel.tag_ids" class="rounded" />{{ t.name }}</label>
              <span v-if="allTags.length === 0" class="text-xs text-gray-400">暂无标签</span>
            </div>
          </div>
          <div v-if="!editingBatch">
            <label class="block text-xs text-gray-500 mb-1">选择学员 (额外)</label>
            <div class="max-h-40 overflow-y-auto space-y-1 border border-gray-100 rounded-lg p-2">
              <label v-for="s in allStudents" :key="s.id" class="flex items-center gap-2 text-xs cursor-pointer hover:bg-gray-50 px-1 py-0.5 rounded"><input type="checkbox" :value="s.id" v-model="panel.student_ids" class="rounded" />{{ s.display_name || s.username }}</label>
            </div>
          </div>
          <div v-if="!editingBatch"><label class="flex items-center gap-2"><input type="checkbox" v-model="panel.autoExclude" class="rounded" /><span class="text-sm text-gray-700">自动排除已完成并通过的学员</span><input v-if="panel.autoExclude" v-model.number="panel.exclude_days" type="number" min="1" class="w-16 px-2 py-1 text-xs border border-gray-200 rounded-lg ml-2" />天内</label></div>
        </div>
        <div class="flex gap-2 mt-4">
          <button @click="confirmSubmit = true" :disabled="!editingBatch && (!panel.student_ids.length && !panel.tag_ids.length)" class="flex-1 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50">确认</button>
          <button @click="closePanel" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg">取消</button>
        </div>
      </div>
    </div>

    <div v-if="detailOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="closeDetail">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-2xl mx-4 p-6 max-h-[85vh] flex flex-col">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-bold text-gray-900">安排明细 — {{ detailBatch?.name || '批次 #'+detailBatch?.id }}</h3>
          <button @click="closeDetail" class="text-gray-400 hover:text-gray-600 text-lg">&times;</button>
        </div>
        <div v-if="detailBatch" class="text-xs text-gray-500 mb-3">{{ detailBatch.start_time ? formatDt(detailBatch.start_time) : '-' }} ~ {{ detailBatch.end_time ? formatDt(detailBatch.end_time) : '-' }}</div>
        <div class="flex-1 overflow-y-auto">
          <div v-if="detailStudents.length === 0" class="text-sm text-gray-400 py-4">暂无学员</div>
          <div v-else class="space-y-2">
            <div v-for="s in detailStudents" :key="s.student_id" class="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
              <div>
                <span class="text-sm text-gray-900">{{ s.student_name }}</span>
                <span class="text-xs ml-2 px-1.5 py-0.5 rounded-full" :class="s.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'">{{ s.status === 'completed' ? '已完成' : '待考' }}</span>
                <span v-if="s.status === 'completed'" class="text-xs text-gray-500 ml-2">得分：{{ s.score }} {{ s.passed ? '通过' : '未通过' }}</span>
              </div>
              <button @click="removeStudent(s)" :disabled="s.status === 'completed'" class="text-xs text-red-500 hover:underline disabled:opacity-50 disabled:cursor-not-allowed" :title="s.status === 'completed' ? '已完成考试的学员不能移除' : ''">移除</button>
            </div>
          </div>
        </div>
        <div class="mt-4 pt-3 border-t border-gray-100 flex items-center gap-2">
          <select v-model="addStudentId" class="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white">
            <option :value="null" disabled>选择学员...</option>
            <option v-for="s in addableStudents" :key="s.id" :value="s.id">{{ s.display_name || s.username }}</option>
          </select>
          <button @click="doAddStudent" :disabled="!addStudentId" class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50">添加</button>
        </div>
      </div>
    </div>

    <div v-if="message" class="mt-4 px-4 py-3 rounded-xl text-sm" :class="msgClass">{{ message }}</div>
    <ConfirmModal :show="confirmSubmit" title="确认" :message="editingBatch ? '将更新此批次信息。' : `将为此批次安排学员参加考试。`" @confirm="doSubmit" @cancel="confirmSubmit = false" />
    <ConfirmModal :show="confirmDelete" title="删除批次" message="确定删除此批次？如有已完成考试的学员则不能删除。" variant="danger" @confirm="doDelete" @cancel="confirmDelete = false" />
    <ConfirmModal :show="confirmRemove" title="移除学员" :message="`确定移除学员「${removingStudent?.student_name}」？`" variant="danger" @confirm="doRemoveStudent" @cancel="confirmRemove = false" />
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
definePageMeta({ middleware: ["auth", "teacher"] });
const { $api } = useNuxtApp();
const route = useRoute();
const examId = computed(() => route.params.id);

const exam = ref(null); const batches = ref([]); const allTags = ref([]); const allStudents = ref([]);
const panelOpen = ref(false); const editingBatch = ref(null);
const panel = ref({ name: "", description: "", start_time: "", end_time: "", duration_minutes: 30, pass_score: 60, tag_ids: [], student_ids: [], autoExclude: true, exclude_days: 60, disabled: false });
const confirmSubmit = ref(false); const confirmDelete = ref(false); const deletingBatch = ref(null);
const detailOpen = ref(false); const detailBatch = ref(null); const detailStudents = ref([]);
const addStudentId = ref(null); const confirmRemove = ref(false); const removingStudent = ref(null);
const message = ref(""); const msgType = ref("success");
const msgClass = computed(() => msgType.value === "success" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700");
const addableStudents = computed(() => {
  const inBatch = new Set(detailStudents.value.map(s => s.student_id));
  return (allStudents.value || []).filter(s => !inBatch.has(s.id));
});

function formatDt(d) { if (!d) return ""; return d.substring(0, 16).replace("T", " "); }

async function fetchAll() {
  try {
    exam.value = (await $api.get(`/exams/${examId.value}`)).data.data;
    const br = await $api.get(`/exams/${examId.value}/batches`);
    batches.value = br.data.data.batches;
    const tr = await $api.get("/tags"); allTags.value = tr.data.data;
    const ur = await $api.get("/users", { params: { role: "student", page_size: 999 } });
    allStudents.value = ur.data.data.items;
  } catch {}
}

function openCreate() {
  editingBatch.value = null;
  panel.value = { name: exam.value?.name || "", description: exam.value?.description || "", start_time: "", end_time: "", duration_minutes: exam.value?.duration_minutes || 30, pass_score: exam.value?.pass_score || 60, tag_ids: [], student_ids: [], autoExclude: true, exclude_days: 60, disabled: false };
  panelOpen.value = true;
}

function openEdit(b) {
  editingBatch.value = b;
  panel.value = { name: b.name || "", description: b.description || "", start_time: "", end_time: "", duration_minutes: b.duration_minutes || 30, pass_score: b.pass_score || 60, tag_ids: [], student_ids: [], autoExclude: false, exclude_days: 60, disabled: b.disabled || false };
  panelOpen.value = true;
}

function closePanel() { panelOpen.value = false; }

async function doSubmit() {
  confirmSubmit.value = false;
  try {
    if (editingBatch.value) {
      await $api.put(`/exams/${examId.value}/batches/${editingBatch.value.id}`, {
        name: panel.value.name, description: panel.value.description,
        duration_minutes: panel.value.duration_minutes, pass_score: panel.value.pass_score,
        disabled: panel.value.disabled,
      });
    } else {
      await $api.post(`/exams/${examId.value}/batches`, {
        name: panel.value.name, description: panel.value.description,
        start_time: panel.value.start_time || null, end_time: panel.value.end_time || null,
        duration_minutes: panel.value.duration_minutes, pass_score: panel.value.pass_score,
        tag_ids: panel.value.tag_ids, student_ids: panel.value.student_ids,
        exclude_completed_days: panel.value.autoExclude ? panel.value.exclude_days : 0,
      });
    }
    showMessage("保存成功", "success"); panelOpen.value = false; fetchAll();
  } catch (e) { showMessage(e.response?.data?.detail || "保存失败", "error"); }
}

function handleDelete(b) { deletingBatch.value = b; confirmDelete.value = true; }
async function doDelete() { confirmDelete.value = false; try { await $api.delete(`/exams/${examId.value}/batches/${deletingBatch.value.id}`); showMessage("已删除", "success"); fetchAll(); } catch (e) { showMessage(e.response?.data?.detail || "删除失败", "error"); } }

async function openDetail(b) {
  detailBatch.value = b;
  detailOpen.value = true;
  try {
    const r = await $api.get(`/exams/${examId.value}/batches/${b.id}`);
    detailStudents.value = r.data.data.students || [];
  } catch { detailStudents.value = []; }
}

function closeDetail() { detailOpen.value = false; detailStudents.value = []; addStudentId.value = null; }

async function doAddStudent() {
  if (!addStudentId.value) return;
  try {
    await $api.post(`/exams/${examId.value}/batches/${detailBatch.value.id}/students`, { student_id: addStudentId.value });
    addStudentId.value = null;
    showMessage("学员已添加", "success");
    openDetail(detailBatch.value); fetchAll();
  } catch (e) { showMessage(e.response?.data?.detail || "添加失败", "error"); }
}

function removeStudent(s) { removingStudent.value = s; confirmRemove.value = true; }
async function doRemoveStudent() {
  confirmRemove.value = false;
  try {
    await $api.delete(`/exams/${examId.value}/batches/${detailBatch.value.id}/students/${removingStudent.value.student_id}`);
    showMessage("学员已移除", "success");
    openDetail(detailBatch.value); fetchAll();
  } catch (e) { showMessage(e.response?.data?.detail || "移除失败", "error"); }
}

function showMessage(msg, type) { message.value = msg; msgType.value = type; setTimeout(() => { message.value = ""; }, 3000); }
fetchAll();
</script>
