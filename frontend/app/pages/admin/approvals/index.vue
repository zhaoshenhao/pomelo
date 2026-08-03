<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-gray-900">文档审批</h2>
        <p class="text-sm text-gray-500 mt-1">管理待审批的文档</p>
      </div>
    </div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
      <h3 class="text-base font-semibold text-gray-900 mb-4">提交新文档</h3>
      <form @submit.prevent="handleUpload" class="space-y-3">
        <div class="flex flex-wrap items-end gap-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">选择文档库 <span class="text-red-500">*</span></label>
            <select v-model="uploadLibraryId" required class="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400">
              <option :value="null" disabled>请选择文档库</option>
              <option v-for="lib in libraries" :key="lib.id" :value="lib.id">{{ lib.name }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">选择文件</label>
            <input ref="fileInput" type="file" accept=".txt,.md,.pdf,.docx,.xlsx,.xls,.pptx" @change="onFileChange" class="text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100" />
          </div>
          <button type="submit" :disabled="!selectedFile || !uploadLibraryId || uploading" class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed">
            {{ uploading ? '提交中...' : '提交审批' }}
          </button>
        </div>
      </form>
    </div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div class="px-4 py-3 border-b border-gray-100">
        <h3 class="text-base font-semibold text-gray-900">待审批文档 <span class="text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-700">{{ approvals.length }}</span></h3>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-left text-gray-600">
            <tr>
              <th class="px-4 py-2 font-medium">文件名</th>
              <th class="px-4 py-2 font-medium">文档库</th>
              <th class="px-4 py-2 font-medium">类型</th>
              <th class="px-4 py-2 font-medium">状态</th>
              <th class="px-4 py-2 font-medium">提交时间</th>
              <th class="px-4 py-2 font-medium">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="item in approvals" :key="item.id" class="hover:bg-gray-50 transition">
              <td class="px-4 py-3 font-medium text-gray-900 max-w-xs truncate">{{ item.original_filename }}</td>
              <td class="px-4 py-3 text-gray-500">{{ item.library_name || '-' }}</td>
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
                  <button @click="openDelete(item)" class="text-xs text-red-500 hover:underline">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="approvals.length === 0" class="px-4 py-12 text-center text-gray-400 text-sm">暂无待审批文档</div>
    </div>

    <div v-if="message" class="mt-4 px-4 py-3 rounded-xl text-sm" :class="msgClass">{{ message }}</div>

    <ConfirmModal :show="deleteModalOpen" title="删除审批" :message="`确定删除审批记录「${deletingItem?.original_filename}」？`" subMessage="该操作将永久删除暂存文件，不可恢复。" variant="danger" @confirm="confirmDelete" @cancel="closeDelete" />
  </div>
</template>

<script setup>
import { ref, computed } from "vue";

definePageMeta({ middleware: ["auth", "teacher"] });

const { $api } = useNuxtApp();
const route = useRoute();

const approvals = ref([]);
const libraries = ref([]);
const selectedFile = ref(null);
const fileInput = ref(null);
const uploadLibraryId = ref(null);
const uploading = ref(false);
const message = ref("");
const msgType = ref("success");
const deleteModalOpen = ref(false);
const deletingItem = ref(null);

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

async function fetchApprovals() {
  try {
    const res = await $api.get("/approvals");
    approvals.value = res.data.data.items;
  } catch {
    showMessage("获取审批列表失败", "error");
  }
}

async function fetchLibraries() {
  try {
    const res = await $api.get("/libraries");
    libraries.value = res.data.data;
  } catch {
    showMessage("获取文档库列表失败", "error");
  }
}

function onFileChange(e) {
  selectedFile.value = e.target.files[0] || null;
}

async function handleUpload() {
  if (!selectedFile.value || !uploadLibraryId.value) return;
  uploading.value = true;
  try {
    const formData = new FormData();
    formData.append("file", selectedFile.value);
    await $api.post(`/approvals?library_id=${uploadLibraryId.value}`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    selectedFile.value = null;
    if (fileInput.value) fileInput.value.value = "";
    showMessage("已提交审批", "success");
    fetchApprovals();
  } catch (e) {
    showMessage(e.response?.data?.detail || "提交失败", "error");
  } finally {
    uploading.value = false;
  }
}

function openDelete(item) {
  deletingItem.value = item;
  deleteModalOpen.value = true;
}

function closeDelete() {
  deleteModalOpen.value = false;
  deletingItem.value = null;
}

async function confirmDelete() {
  const item = deletingItem.value;
  closeDelete();
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

fetchLibraries();
fetchApprovals();
</script>
