<template>
  <div>
    <div class="mb-4">
      <NuxtLink :to="`/admin/libraries/${libraryId}`" class="text-sm text-primary-600 hover:underline">&larr; 返回文档管理</NuxtLink>
    </div>

    <div class="mb-6">
      <h2 class="text-xl font-bold text-gray-900">备份查看和恢复</h2>
      <p class="text-sm text-gray-500 mt-1">文档库备份列表，点击文档查看内容</p>
    </div>

    <div v-if="loading" class="text-center py-8 text-gray-400 text-sm">加载中...</div>

    <template v-else>
      <!-- Top: Backup List -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 mb-4">
        <div class="px-4 py-3 bg-gray-50 border-b border-gray-200 text-sm font-semibold text-gray-700">备份列表</div>
        <div v-if="backups.length === 0" class="px-4 py-8 text-center text-gray-400 text-sm">暂无备份</div>
        <div v-for="(b, bi) in backups" :key="b.filename" class="border-b border-gray-100 last:border-0">
          <div class="px-4 py-3 bg-gray-50/50 flex items-center justify-between">
            <div class="flex items-center gap-4 text-xs">
              <span class="font-medium text-gray-800">{{ b.filename }}</span>
              <span class="text-gray-500">{{ formatSize(b.size) }}</span>
              <span class="text-gray-400">{{ formatDate(b.created_at) }}</span>
            </div>
          </div>
          <div v-if="backupDocs[b.filename] === undefined" class="px-4 py-2 text-gray-400 text-xs">加载文档列表...</div>
          <div v-else-if="backupDocs[b.filename].length === 0" class="px-4 py-2 text-gray-400 text-xs">此备份无文档</div>
          <table v-else class="w-full text-xs">
            <thead class="bg-gray-50/30 text-left text-gray-500">
              <tr>
                <th class="px-4 py-1.5 font-medium">文档名</th>
                <th class="px-4 py-1.5 font-medium">大小</th>
                <th class="px-4 py-1.5 font-medium">修改时间</th>
                <th class="px-4 py-1.5 font-medium w-16"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="doc in backupDocs[b.filename]" :key="doc.name" class="hover:bg-gray-50">
                <td class="px-4 py-2 font-medium text-gray-800">{{ doc.name }}</td>
                <td class="px-4 py-2 text-gray-500">{{ formatSize(doc.size) }}</td>
                <td class="px-4 py-2 text-gray-400">{{ formatDate(doc.modified_at) }}</td>
                <td class="px-4 py-2">
                  <button
                    @click="viewDocument(b.filename, doc.name)"
                    class="text-xs text-primary-600 hover:underline whitespace-nowrap"
                  >查看</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Middle: Markdown Display Area -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 mb-4">
        <div class="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-200">
          <span class="text-xs font-medium text-gray-600">
            {{ displayViewMode === 'text' ? '纯文本' : '语法高亮' }}
            <span v-if="displayDocName" class="text-gray-400 ml-2">{{ displayDocName }}</span>
          </span>
          <button @click="toggleViewMode" class="text-xs px-3 py-1 rounded-md border border-gray-300 hover:bg-white transition">
            {{ displayViewMode === 'text' ? '语法高亮' : '纯文本' }}
          </button>
        </div>
        <div v-if="displayContent === '' && !displayLoading" class="px-4 py-16 text-center text-gray-400 text-sm">
          选择一个文档查看内容
        </div>
        <div v-else-if="displayLoading" class="px-4 py-16 text-center text-gray-400 text-sm">
          加载内容...
        </div>
        <div v-else-if="displayViewMode === 'text'" class="overflow-auto p-4 max-h-96">
          <pre class="text-xs font-mono text-gray-700 whitespace-pre-wrap">{{ displayContent }}</pre>
        </div>
        <div v-else class="overflow-auto p-4 max-h-96">
          <div class="markdown-body" v-html="renderedContent"></div>
        </div>
      </div>

      <!-- Bottom: Exit and Restore -->
      <div class="flex items-center justify-between">
        <NuxtLink :to="`/admin/libraries/${libraryId}`" class="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 transition">退出</NuxtLink>
        <button @click="restoreModalOpen = true" :disabled="backups.length === 0" class="px-6 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition">恢复此备份</button>
      </div>
    </template>

    <div v-if="message" class="mt-4 px-4 py-3 rounded-xl text-sm" :class="msgClass">{{ message }}</div>

    <ConfirmModal
      :show="restoreModalOpen"
      title="恢复备份"
      :message="`确定将文档库恢复至备份「${restoreBackupName}」的状态？`"
      sub-message="当前库内所有文档将被删除并替换为此备份的内容，此操作不可撤销。"
      variant="danger"
      confirm-text="确认恢复"
      @confirm="executeRestore"
      @cancel="restoreModalOpen = false"
    />
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { marked } from "marked";
import { sanitizeHtml } from "@/utils/sanitize";

definePageMeta({ middleware: ["auth", "teacher"] });

const { $api } = useNuxtApp();
const route = useRoute();

const libraryId = computed(() => route.params.id);
const selectedBackup = computed(() => route.query.backup || "");
const loading = ref(true);
const backups = ref([]);
const backupDocs = ref({});
const displayLoading = ref(false);
const displayDocName = ref("");
const displayContent = ref("");
const displayViewMode = ref("text");
const message = ref("");
const msgType = ref("success");
const restoreModalOpen = ref(false);
const restoreBackupName = ref("");

const msgClass = computed(() =>
  msgType.value === "success"
    ? "bg-green-50 text-green-700 border border-green-200"
    : "bg-red-50 text-red-700 border border-red-200"
);

const renderedContent = computed(() => sanitizeHtml(marked(displayContent.value)));

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

function toggleViewMode() {
  displayViewMode.value = displayViewMode.value === "text" ? "highlight" : "text";
}

function showMessage(msg, type) {
  message.value = msg;
  msgType.value = type;
  setTimeout(() => { message.value = ""; }, 3000);
}

async function fetchBackups() {
  try {
    const res = await $api.get(`/libraries/${libraryId.value}/backups`);
    const allBackups = res.data.data;
    if (selectedBackup.value) {
      const matched = allBackups.find((b) => b.filename === selectedBackup.value);
      backups.value = matched ? [matched] : [];
      restoreBackupName.value = selectedBackup.value;
      await fetchBackupDocs(selectedBackup.value);
    } else {
      backups.value = allBackups;
      for (const b of backups.value) {
        fetchBackupDocs(b.filename);
      }
    }
  } catch {
    showMessage("获取备份列表失败", "error");
  } finally {
    loading.value = false;
  }
}

async function fetchBackupDocs(backupFilename) {
  try {
    const res = await $api.get(`/libraries/${libraryId.value}/backups/${backupFilename}`);
    backupDocs.value[backupFilename] = res.data.data;
  } catch {
    backupDocs.value[backupFilename] = [];
  }
}

async function viewDocument(backupFilename, docName) {
  displayLoading.value = true;
  restoreBackupName.value = backupFilename;
  try {
    const res = await $api.get(
      `/libraries/${libraryId.value}/backups/${backupFilename}/documents/${encodeURIComponent(docName)}/content`
    );
    displayDocName.value = docName;
    displayContent.value = res.data.data.content;
  } catch {
    showMessage("加载文档内容失败", "error");
  } finally {
    displayLoading.value = false;
  }
}

async function executeRestore() {
  restoreModalOpen.value = false;
  try {
    await $api.post(`/libraries/${libraryId.value}/backups/${restoreBackupName.value}/restore`);
    showMessage("文档库已恢复", "success");
    setTimeout(() => {
      navigateTo(`/admin/libraries/${libraryId.value}`);
    }, 800);
  } catch (e) {
    showMessage(e.response?.data?.detail || "恢复失败", "error");
  }
}

fetchBackups();
</script>
