<template>
  <div>
    <div class="mb-4">
      <NuxtLink to="/admin/libraries" class="text-sm text-primary-600 hover:underline">&larr; 返回文档库列表</NuxtLink>
    </div>

    <div class="mb-6 flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-gray-900">{{ library?.name || '文档库' }}</h2>
        <p class="text-sm text-gray-500 mt-1">{{ library?.description || '' }}</p>
      </div>
    </div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6" v-if="!editPanelOpen">
      <h3 class="text-base font-semibold text-gray-900 mb-4">上传文档（进入审批流程）</h3>
      <form @submit.prevent="handleUpload" class="flex flex-wrap items-end gap-3">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">选择文件</label>
          <input ref="fileInput" type="file" accept=".txt,.md,.pdf,.docx,.xlsx,.xls,.pptx" @change="onFileChange"
            class="text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100" />
        </div>
        <button type="submit" :disabled="!selectedFile || uploading"
          class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed">
          {{ uploading ? '提交中...' : '提交审批' }}
        </button>
      </form>
    </div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden" v-if="!editPanelOpen">
      <div class="flex border-b border-gray-200">
        <button @click="activeTab = 0"
          class="px-4 py-3 text-sm font-medium transition border-b-2 -mb-px"
          :class="activeTab === 0 ? 'text-primary-700 border-primary-600' : 'text-gray-500 border-transparent hover:text-gray-700'">
          文档列表 <span class="text-xs px-2 py-0.5 rounded-full bg-green-50 text-green-700">{{ documents.length }}</span>
        </button>
        <button @click="activeTab = 1" :disabled="approvals.length === 0"
          class="px-4 py-3 text-sm font-medium transition border-b-2 -mb-px"
          :class="activeTab === 1 ? 'text-primary-700 border-primary-600' : (approvals.length === 0 ? 'text-gray-300 cursor-not-allowed' : 'text-gray-500 border-transparent hover:text-gray-700')">
          审批列表 <span class="text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-700">{{ approvals.length }}</span>
        </button>
        <button @click="activeTab = 2"
          class="px-4 py-3 text-sm font-medium transition border-b-2 -mb-px"
          :class="activeTab === 2 ? 'text-primary-700 border-primary-600' : 'text-gray-500 border-transparent hover:text-gray-700'">
          备份列表 <span class="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-700">{{ backups.length }}</span>
        </button>
      </div>

      <!-- Document List Tab -->
      <div v-if="activeTab === 0">
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-gray-50 text-left text-gray-600">
              <tr>
                <th class="px-4 py-2 font-medium">文件名</th>
                <th class="px-4 py-2 font-medium">上传时间</th>
                <th class="px-4 py-2 font-medium">操作</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="doc in documents" :key="doc.id" class="hover:bg-gray-50 transition">
                <td class="px-4 py-3 font-medium text-gray-900">{{ doc.filename }}</td>
                <td class="px-4 py-3 text-gray-400 text-xs">{{ formatDate(doc.created_at) }}</td>
                <td class="px-4 py-3">
                  <div class="flex items-center gap-2">
                    <button @click="openEditPanel(doc)" class="text-xs text-primary-600 hover:underline">查看和编辑</button>
                    <button @click="openDocDeleteModal(doc)" class="text-xs text-red-500 hover:underline">删除</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="documents.length === 0" class="px-4 py-12 text-center text-gray-400 text-sm">暂无文档</div>
      </div>

      <!-- Approval List Tab -->
      <div v-if="activeTab === 1">
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-gray-50 text-left text-gray-600">
              <tr>
                <th class="px-4 py-2 font-medium">文件名</th>
                <th class="px-4 py-2 font-medium">类型</th>
                <th class="px-4 py-2 font-medium">状态</th>
                <th class="px-4 py-2 font-medium">提交时间</th>
                <th class="px-4 py-2 font-medium">操作</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="item in approvals" :key="item.id" class="hover:bg-gray-50 transition">
                <td class="px-4 py-3 font-medium text-gray-900 max-w-xs truncate">{{ item.original_filename }}</td>
                <td class="px-4 py-3">
                  <span class="text-xs px-2 py-0.5 rounded-full" :class="typeBadge(item.file_type)">{{ typeLabel(item.file_type) }}</span>
                </td>
                <td class="px-4 py-3">
                  <span class="text-xs px-2 py-0.5 rounded-full" :class="statusBadge(item.status)">{{ statusLabel(item.status) }}</span>
                </td>
                <td class="px-4 py-3 text-gray-400 text-xs">{{ formatDate(item.created_at) }}</td>
                <td class="px-4 py-3">
                  <div class="flex items-center gap-2">
                    <NuxtLink :to="`/admin/approvals/${item.id}`" class="text-xs text-primary-600 hover:underline">审批</NuxtLink>
                    <button @click="openApprovalDelete(item)" class="text-xs text-red-500 hover:underline">删除</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="approvals.length === 0" class="px-4 py-12 text-center text-gray-400 text-sm">暂无待审批文档</div>
      </div>

      <!-- Backup List Tab -->
      <div v-if="activeTab === 2">
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-gray-50 text-left text-gray-600">
              <tr>
                <th class="px-4 py-2 font-medium">文件名</th>
                <th class="px-4 py-2 font-medium">大小</th>
                <th class="px-4 py-2 font-medium">创建时间</th>
                <th class="px-4 py-2 font-medium">操作</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="b in backups" :key="b.filename" class="hover:bg-gray-50 transition">
                <td class="px-4 py-3 font-medium text-gray-900 text-xs">{{ b.filename }}</td>
                <td class="px-4 py-3 text-gray-500 text-xs">{{ formatSize(b.size) }}</td>
                <td class="px-4 py-3 text-gray-400 text-xs">{{ formatDate(b.created_at) }}</td>
                <td class="px-4 py-3">
                  <NuxtLink :to="`/admin/backups/${libraryId}?backup=${encodeURIComponent(b.filename)}`" class="text-xs text-primary-600 hover:underline">查看和恢复</NuxtLink>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="backups.length === 0" class="px-4 py-12 text-center text-gray-400 text-sm">暂无备份</div>
      </div>
    </div>

    <div v-if="message" class="mt-4 px-4 py-3 rounded-xl text-sm" :class="msgClass">{{ message }}</div>

    <!-- Document Edit Panel -->
    <div v-if="editPanelOpen" class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden" style="height: calc(100vh - 180px); min-height: 400px;">
      <div class="flex flex-col h-full">
        <div class="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200 shrink-0">
          <h3 class="text-sm font-semibold text-gray-900">{{ editingDoc?.filename }}</h3>
          <button @click="closeEditPanel" class="text-gray-400 hover:text-gray-600 text-lg leading-none">&times;</button>
        </div>
        <div class="flex-1 min-h-0">
          <MarkdownEditor v-model="editingContent" />
        </div>
        <div class="flex items-center justify-end gap-3 px-4 py-3 border-t border-gray-200 bg-gray-50 shrink-0">
          <button @click="closeEditPanel" class="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-white transition">取消</button>
          <button @click="saveEdit" :disabled="editingSaving" class="px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition">确认</button>
        </div>
      </div>
    </div>

    <!-- Doc Delete Confirm -->
    <ConfirmModal :show="docDeleteModalOpen" title="删除文档" :message="`确定删除文档「${deletingDoc?.filename}」？`" variant="danger" @confirm="confirmDocDelete" @cancel="closeDocDeleteModal" />

    <!-- Approval Delete Confirm -->
    <ConfirmModal :show="approvalDeleteModalOpen" title="删除审批" :message="`确定删除审批记录「${deletingApproval?.original_filename}」？`" subMessage="该操作将永久删除暂存文件，不可恢复。" variant="danger" @confirm="confirmApprovalDelete" @cancel="closeApprovalDeleteModal" />
  </div>
</template>

<script setup>
import { ref, computed } from "vue";

definePageMeta({ middleware: ["auth", "teacher"] });

const { $api } = useNuxtApp();
const route = useRoute();

const libraryId = computed(() => route.params.id);
const activeTab = ref(0);
const library = ref(null);
const documents = ref([]);
const approvals = ref([]);
const backups = ref([]);
const selectedFile = ref(null);
const fileInput = ref(null);
const uploading = ref(false);
const message = ref("");
const msgType = ref("success");

const editPanelOpen = ref(false);
const editingDoc = ref(null);
const editingContent = ref("");
const editingSaving = ref(false);
const docDeleteModalOpen = ref(false);
const deletingDoc = ref(null);
const approvalDeleteModalOpen = ref(false);
const deletingApproval = ref(null);

const msgClass = computed(() => msgType.value === "success" ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200");

function typeLabel(t) {
  const map = { text: "文本", markdown: "Markdown", word: "Word", pdf: "PDF", excel: "Excel", ppt: "PPT" };
  return map[t] || t;
}

function typeBadge(t) {
  const map = { markdown: "bg-blue-50 text-blue-700", word: "bg-indigo-50 text-indigo-700", pdf: "bg-red-50 text-red-700", excel: "bg-green-50 text-green-700", text: "bg-gray-50 text-gray-700", ppt: "bg-orange-50 text-orange-700" };
  return map[t] || "bg-gray-50 text-gray-600";
}

function statusLabel(s) {
  const map = { new: "新文档", content_review: "内容审核", rewrite: "文字改写", preview: "预览", completed: "已完成", deleted: "已删除" };
  return map[s] || s;
}

function statusBadge(s) {
  const map = { new: "bg-blue-50 text-blue-700", content_review: "bg-purple-50 text-purple-700", rewrite: "bg-amber-50 text-amber-700", preview: "bg-cyan-50 text-cyan-700", completed: "bg-green-50 text-green-700", deleted: "bg-red-50 text-red-700" };
  return map[s] || "bg-gray-50 text-gray-600";
}

function formatDate(d) {
  return d ? d.substring(0, 16).replace("T", " ") : "";
}

function formatSize(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  let size = bytes;
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i++; }
  return size.toFixed(1) + " " + units[i];
}

async function fetchLibrary() {
  try {
    const res = await $api.get(`/libraries/${libraryId.value}`);
    library.value = res.data.data;
  } catch {
    showMessage("获取文档库信息失败", "error");
  }
}

async function fetchDocuments() {
  try {
    const res = await $api.get(`/libraries/${libraryId.value}/documents`);
    documents.value = res.data.data.items;
  } catch {
    showMessage("获取文档列表失败", "error");
  }
}

async function fetchApprovals() {
  try {
    const res = await $api.get(`/approvals?library_id=${libraryId.value}`);
    approvals.value = res.data.data.items;
  } catch {}
}

async function fetchBackups() {
  try {
    const res = await $api.get(`/libraries/${libraryId.value}/backups`);
    backups.value = res.data.data;
  } catch {}
}

function onFileChange(e) {
  selectedFile.value = e.target.files[0] || null;
}

async function handleUpload() {
  if (!selectedFile.value) return;
  uploading.value = true;
  try {
    const formData = new FormData();
    formData.append("file", selectedFile.value);
    await $api.post(`/approvals?library_id=${libraryId.value}`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    selectedFile.value = null;
    if (fileInput.value) fileInput.value.value = "";
    showMessage("已提交审批，可在审批列表中查看", "success");
    fetchApprovals();
    activeTab.value = 1;
  } catch (e) {
    showMessage(e.response?.data?.detail || "提交失败", "error");
  } finally {
    uploading.value = false;
  }
}

async function openEditPanel(doc) {
  editingDoc.value = doc;
  editingContent.value = "";
  editPanelOpen.value = true;
  try {
    const res = await $api.get(`/libraries/documents/${doc.id}/content`);
    editingContent.value = res.data.data.content;
  } catch {
    showMessage("加载文档内容失败", "error");
    editingContent.value = "";
  }
}

function closeEditPanel() {
  editPanelOpen.value = false;
  editingDoc.value = null;
  editingContent.value = "";
}

async function saveEdit() {
  if (!editingDoc.value) return;
  editingSaving.value = true;
  try {
    await $api.put(`/libraries/documents/${editingDoc.value.id}/content`, {
      content: editingContent.value,
    });
    showMessage("已保存", "success");
    closeEditPanel();
    fetchDocuments();
  } catch (e) {
    showMessage(e.response?.data?.detail || "保存失败", "error");
  } finally {
    editingSaving.value = false;
  }
}

function openDocDeleteModal(doc) {
  deletingDoc.value = doc;
  docDeleteModalOpen.value = true;
}

function closeDocDeleteModal() {
  docDeleteModalOpen.value = false;
  deletingDoc.value = null;
}

async function confirmDocDelete() {
  const docId = deletingDoc.value.id;
  closeDocDeleteModal();
  try {
    await $api.delete(`/libraries/documents/${docId}`);
    documents.value = documents.value.filter((d) => d.id !== docId);
    showMessage("已删除", "success");
  } catch (e) {
    showMessage(e.response?.data?.detail || "删除失败", "error");
  }
}

function openApprovalDelete(item) {
  deletingApproval.value = item;
  approvalDeleteModalOpen.value = true;
}

function closeApprovalDeleteModal() {
  approvalDeleteModalOpen.value = false;
  deletingApproval.value = null;
}

async function confirmApprovalDelete() {
  const item = deletingApproval.value;
  closeApprovalDeleteModal();
  try {
    await $api.delete(`/approvals/${item.id}`);
    approvals.value = approvals.value.filter((a) => a.id !== item.id);
    showMessage("已删除", "success");
  } catch (e) {
    showMessage(e.response?.data?.detail || "删除失败", "error");
  }
}

function showMessage(msg, type) {
  message.value = msg;
  msgType.value = type;
  setTimeout(() => { message.value = ""; }, 3000);
}

fetchLibrary();
fetchDocuments();
fetchApprovals();
fetchBackups();
</script>
