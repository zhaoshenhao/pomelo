<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-gray-900">题库管理</h2>
        <p class="text-sm text-gray-500 mt-1">生成和管理基于文档库的试题题库</p>
      </div>
      <button @click="openGenerate" class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 transition shadow-sm">+ 生成题库</button>
    </div>

    <div class="mb-4">
      <input v-model="search" @input="onSearchInput" placeholder="搜索题库名称..." class="w-full max-w-sm px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" />
    </div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <table class="w-full text-sm"><thead class="bg-gray-50 text-left text-gray-600"><tr><th class="px-4 py-3 font-medium">名称</th><th class="px-4 py-3 font-medium">描述</th><th class="px-4 py-3 font-medium">题目数</th><th class="px-4 py-3 font-medium">各题型</th><th class="px-4 py-3 font-medium">禁止</th><th class="px-4 py-3 font-medium">生成人</th><th class="px-4 py-3 font-medium">生成日期</th><th class="px-4 py-3 font-medium">操作</th></tr></thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="item in items" :key="item.id" class="hover:bg-gray-50 transition">
            <td class="px-4 py-3 font-medium text-gray-900 max-w-xs truncate">{{ item.name }}</td>
            <td class="px-4 py-3 text-gray-500 max-w-xs truncate">{{ item.description || '-' }}</td>
            <td class="px-4 py-3 text-gray-700 text-center">{{ item.question_count }}</td>
            <td class="px-4 py-3 text-gray-500 text-xs">{{ formatTypeCounts(item.type_counts) }}</td>
            <td class="px-4 py-3"><span :class="item.disabled ? 'text-red-500 bg-red-50 border border-red-200' : 'text-green-600 bg-green-50 border border-green-200'" class="px-2 py-0.5 rounded text-xs">{{ item.disabled ? '已禁止' : '正常' }}</span></td>
            <td class="px-4 py-3 text-gray-500">{{ item.creator_name }}</td>
            <td class="px-4 py-3 text-gray-400 text-xs">{{ formatDate(item.created_at) }}</td>
            <td class="px-4 py-3">
              <div class="flex items-center gap-2">
                <NuxtLink :to="`/admin/question-banks/${item.id}/browse`" class="text-xs text-primary-600 hover:underline">浏览</NuxtLink>
                <NuxtLink :to="`/admin/question-banks/${item.id}/drills`" class="text-xs text-primary-600 hover:underline">训练汇总</NuxtLink>
                <button @click="openEdit(item)" class="text-xs text-primary-600 hover:underline">编辑</button>
                <button @click="handleDelete(item)" class="text-xs text-red-500 hover:underline">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="items.length === 0 && !loading" class="px-4 py-12 text-center text-gray-400 text-sm">{{ search ? '没有匹配的题库' : '暂无题库' }}</div>
      <div class="px-4 py-3 border-t border-gray-100 flex items-center justify-between"><span class="text-sm text-gray-500">共 {{ total }} 条</span><div class="flex items-center gap-2"><button @click="page--; fetchList()" :disabled="page <= 1" class="px-3 py-1 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50">上一页</button><span class="text-sm text-gray-500">第 {{ page }} / {{ totalPages }} 页</span><button @click="page++; fetchList()" :disabled="page >= totalPages" class="px-3 py-1 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50">下一页</button></div></div>
    </div>

    <div v-if="genOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="closeGenerate">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 p-6 max-h-[90vh] overflow-y-auto">
        <h3 class="text-lg font-bold text-gray-900 mb-4">生成题库</h3>
        <div class="space-y-4 text-sm">
          <div><label class="block text-sm font-medium text-gray-700 mb-1">选择文档库</label><select v-model="gen.library_id" @change="onLibraryChange" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white"><option :value="null" disabled>请选择文档库</option><option v-for="l in libraries" :key="l.id" :value="l.id">{{ l.name }}</option></select></div>
          <div v-if="libraryDocs.length"><label class="block text-sm font-medium text-gray-700 mb-1">选择文档 (至少选1个)</label><div class="space-y-1 max-h-40 overflow-y-auto border border-gray-100 rounded-lg p-2"><label v-for="d in libraryDocs" :key="d.filename" class="flex items-center gap-2 px-2 py-1 rounded hover:bg-gray-50 cursor-pointer text-xs"><input type="checkbox" :value="d.filename" v-model="gen.document_names" class="w-3.5 h-3.5" />{{ d.filename }}</label></div></div>
          <div><label class="block text-sm font-medium text-gray-700 mb-1">出题提示词</label><select v-model="gen.prompt_id" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white"><option :value="null" disabled>请选择提示词</option><option v-for="p in examPrompts" :key="p.id" :value="p.id">{{ p.name }}</option></select></div>
          <div><label class="block text-xs text-gray-500 mb-1">名称 <span class="text-red-500">*</span></label><input v-model="gen.name" required class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" /></div>
          <div><label class="block text-xs text-gray-500 mb-1">描述</label><textarea v-model="gen.description" rows="2" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"></textarea></div>
        </div>
        <div class="flex gap-2 pt-4"><button @click="confirmGen = true" :disabled="!canGen || generating" class="flex-1 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50">{{ generating ? '生成中...' : '生成题库' }}</button><button @click="closeGenerate" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg">取消</button></div>
      </div>
    </div>

    <div v-if="genDirtyConfirm" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/60">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm mx-4 p-6 text-center">
        <div class="text-2xl mb-3">&#x26A0;&#xFE0F;</div>
        <h3 class="text-lg font-bold text-gray-900 mb-2">放弃填写？</h3>
        <p class="text-sm text-gray-500 mb-4">已输入的内容将丢失。</p>
        <div class="flex gap-3"><button @click="forceCloseGenerate" class="flex-1 py-2 bg-red-500 text-white text-sm rounded-lg hover:bg-red-600">放弃并关闭</button><button @click="genDirtyConfirm = false" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50">继续填写</button></div>
      </div>
    </div>

    <div v-if="editModalOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="closeEdit">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 p-6"><h3 class="text-lg font-bold text-gray-900 mb-4">编辑题库</h3>
        <form @submit.prevent="handleEditSubmit" class="space-y-3"><div><label class="block text-sm font-medium text-gray-700 mb-1">名称</label><input v-model="editForm.name" required class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg" /></div><div><label class="block text-sm font-medium text-gray-700 mb-1">描述</label><textarea v-model="editForm.description" rows="2" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg"></textarea></div>
          <div><label class="flex items-center gap-2"><input type="checkbox" v-model="editForm.disabled" class="rounded" /><span class="text-sm text-gray-700">禁止（禁止后无法用于生成试卷）</span></label></div>
          <div class="flex gap-2 pt-2"><button type="submit" class="flex-1 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700">保存</button><button type="button" @click="closeEdit" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg">取消</button></div>
        </form>
      </div>
    </div>

    <div v-if="editConfirmClose" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/60">
      <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm mx-4 p-6 text-center">
        <div class="text-2xl mb-3">&#x26A0;&#xFE0F;</div>
        <h3 class="text-lg font-bold text-gray-900 mb-2">放弃修改？</h3>
        <p class="text-sm text-gray-500 mb-4">未保存的修改将丢失。</p>
        <div class="flex gap-3"><button @click="forceCloseEdit" class="flex-1 py-2 bg-red-500 text-white text-sm rounded-lg hover:bg-red-600">放弃并关闭</button><button @click="editConfirmClose = false" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50">继续编辑</button></div>
      </div>
    </div>

    <div v-if="message" class="mt-4 px-4 py-3 rounded-xl text-sm" :class="msgClass">{{ message }}</div>
    <ConfirmModal :show="deleteOpen" title="删除题库" :message="`确定删除题库「${deletingItem?.name}」？`" variant="danger" @confirm="confirmDelete" @cancel="deleteOpen = false" />
    <ConfirmModal :show="confirmGen" title="确认生成" message="将调用 AI 生成试题，可能需要 1-2 分钟。确认继续？" @confirm="doGen" @cancel="confirmGen = false" />

    <div v-if="generating" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/60">
      <div class="bg-white rounded-2xl shadow-xl px-8 py-6 text-center">
        <div class="inline-block w-8 h-8 border-4 border-primary-400 border-t-transparent rounded-full animate-spin mb-4"></div>
        <p class="text-sm text-gray-700 font-medium">正在生成题库，AI 生成可能需要 1-2 分钟，请稍候...</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
definePageMeta({ middleware: ["auth", "teacher"] });
const { $api } = useNuxtApp();

const items = ref([]); const total = ref(0); const page = ref(1); const pageSize = 20; const loading = ref(false);
const search = ref(""); const message = ref(""); const msgType = ref("success");
const deleteOpen = ref(false); const deletingItem = ref(null);
const editModalOpen = ref(false); const editingItem = ref(null); const editForm = ref({}); const editFormSnapshot = ref({}); const editConfirmClose = ref(false);
const genOpen = ref(false); const generating = ref(false); const confirmGen = ref(false); const genDirtyConfirm = ref(false);
const libraries = ref([]); const libraryDocs = ref([]); const examPrompts = ref([]);
const gen = ref({ library_id: null, document_names: [], prompt_id: null, name: "", description: "" });
const genSnapshot = ref({});
let searchTimer;

const totalPages = computed(() => Math.ceil(total.value / pageSize) || 1);
const msgClass = computed(() => msgType.value === "success" ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200");
const canGen = computed(() => gen.value.library_id && gen.value.prompt_id && gen.value.name.trim() && gen.value.document_names.length > 0);
const isGenDirty = computed(() => {
  const g = gen.value; const s = genSnapshot.value;
  return g.library_id !== (s.library_id || null)
    || g.prompt_id !== (s.prompt_id || null)
    || g.name !== (s.name || "")
    || g.description !== (s.description || "")
    || (g.document_names || []).sort().join(",") !== (s.document_names || []).sort().join(",");
});
const isEditDirty = computed(() => {
  const f = editForm.value; const s = editFormSnapshot.value;
  return f.name !== (s.name || "")
    || f.description !== (s.description || "")
    || f.disabled !== s.disabled;
});

function formatDate(d) { if (!d) return ""; return d.substring(0, 16).replace("T", " "); }
const TYPE_NAMES = { single: "单选", multiple: "多选", true_false: "判断", fill: "填空", match: "匹配" };
function formatTypeCounts(tc) { if (!tc || Object.keys(tc).length === 0) return "-"; return Object.entries(tc).map(([k, v]) => `${TYPE_NAMES[k] || k}${v}`).join("/"); }
function onSearchInput() { clearTimeout(searchTimer); searchTimer = setTimeout(() => { page.value = 1; fetchList(); }, 300); }

async function fetchList() { loading.value = true; try { const p = { page: page.value, page_size: pageSize }; if (search.value) p.search = search.value; const r = await $api.get("/question-banks", { params: p }); items.value = r.data.data.items; total.value = r.data.data.total; } catch {} finally { loading.value = false; } }

async function fetchLibraries() { try { const r = await $api.get("/libraries"); libraries.value = r.data.data; } catch {} }
async function onLibraryChange() { gen.value.document_names = []; libraryDocs.value = []; if (!gen.value.library_id) return; try { const r = await $api.get(`/libraries/${gen.value.library_id}/documents`); libraryDocs.value = r.data.data.items; } catch {} }
async function fetchExamPrompts() { try { const r = await $api.get("/ai-prompts", { params: { type: "exam" } }); examPrompts.value = r.data.data; } catch {} }

function openGenerate() { gen.value = { library_id: null, document_names: [], prompt_id: null, name: "", description: "" }; genSnapshot.value = { ...gen.value, document_names: [...gen.value.document_names] }; confirmGen.value = false; generating.value = false; genDirtyConfirm.value = false; genOpen.value = true; fetchLibraries(); fetchExamPrompts(); }
function closeGenerate() { if (isGenDirty.value) { genDirtyConfirm.value = true; return; } genOpen.value = false; }
function forceCloseGenerate() { genDirtyConfirm.value = false; genOpen.value = false; }
async function doGen() { confirmGen.value = false; generating.value = true; try { const r = await $api.post("/question-banks/generate", gen.value); pollJob(r.data.data.job_id); } catch (e) { showMessage(e.response?.data?.detail || "生成失败", "error"); generating.value = false; } }

let pollTimer = null;
async function pollJob(jobId) {
  pollTimer = setInterval(async () => {
    try {
      const r = await $api.get(`/question-banks/generate/${jobId}`);
      const job = r.data.data;
      if (job.status === "done") { clearInterval(pollTimer); generating.value = false; genSnapshot.value = { ...gen.value, document_names: [...gen.value.document_names] }; genOpen.value = false; fetchList(); showMessage("生成成功", "success"); }
      else if (job.status === "failed") { clearInterval(pollTimer); generating.value = false; showMessage(job.error || "生成失败", "error"); }
    } catch { clearInterval(pollTimer); generating.value = false; showMessage("生成状态查询失败", "error"); }
  }, 3000);
}

function openEdit(item) { editingItem.value = item; editForm.value = { name: item.name, description: item.description, disabled: item.disabled || false }; editFormSnapshot.value = { name: item.name, description: item.description || "", disabled: item.disabled || false }; editConfirmClose.value = false; editModalOpen.value = true; }
function closeEdit() { if (isEditDirty.value) { editConfirmClose.value = true; return; } editModalOpen.value = false; }
function forceCloseEdit() { editConfirmClose.value = false; editModalOpen.value = false; }
async function handleEditSubmit() { try { await $api.put(`/question-banks/${editingItem.value.id}`, { name: editForm.value.name, description: editForm.value.description, disabled: editForm.value.disabled }); Object.assign(editingItem.value, editForm.value); showMessage("更新成功", "success"); editModalOpen.value = false; } catch (e) { showMessage(e.response?.data?.detail || "更新失败", "error"); } }

function handleDelete(item) { deletingItem.value = item; deleteOpen.value = true; }
async function confirmDelete() { deleteOpen.value = false; try { await $api.delete(`/question-banks/${deletingItem.value.id}`); items.value = items.value.filter(i => i.id !== deletingItem.value.id); total.value--; showMessage("已删除", "success"); } catch (e) { showMessage(e.response?.data?.detail || "删除失败", "error"); } }

function showMessage(msg, type) { message.value = msg; msgType.value = type; setTimeout(() => { message.value = ""; }, 3000); }

fetchList();
</script>
