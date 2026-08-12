<template>
  <div>
    <div class="mb-4">
      <NuxtLink to="/admin/study-materials" class="text-sm text-primary-600 hover:underline">&larr; 返回学习资料列表</NuxtLink>
    </div>

    <h2 class="text-xl font-bold text-gray-900 mb-6">新建学习资料</h2>

    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-6">
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">1. 选择文档库</label>
        <select v-model="selectedLibraryId" @change="onLibraryChange" class="w-full max-w-md px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400">
          <option :value="null" disabled>请选择文档库</option>
          <option v-for="lib in libraries" :key="lib.id" :value="lib.id">{{ lib.name }}</option>
        </select>
        <p v-if="libraryDocs.length > 0" class="text-xs text-gray-400 mt-1">文档库共 {{ libraryDocs.length }} 个文档</p>
      </div>

      <div v-if="libraryDocs.length > 0">
        <label class="block text-sm font-medium text-gray-700 mb-2">
          2. 选择文档
          <button @click="toggleSelectAll" class="ml-3 text-xs text-primary-600 hover:underline">
            {{ selectedDocs.length === libraryDocs.length ? '取消全选' : '全选整个文档库' }}
          </button>
        </label>
        <div class="space-y-1 max-h-60 overflow-y-auto border border-gray-100 rounded-lg p-2">
          <label v-for="doc in libraryDocs" :key="doc.filename" class="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-50 cursor-pointer">
            <input type="checkbox" :value="doc.filename" v-model="selectedDocs" class="w-4 h-4 text-primary-600 border-gray-300 rounded" />
            <span class="text-sm text-gray-700">{{ doc.filename }}</span>
          </label>
        </div>
        <p v-if="selectedDocs.length === 0" class="text-xs text-amber-500 mt-1">未选择任何文档，将使用整个文档库的所有文档</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">3. 选择风格提示词</label>
        <select v-model="selectedPromptId" class="w-full max-w-md px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400">
          <option :value="null" disabled>请选择提示词</option>
          <option v-for="p in studyPrompts" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
        <p v-if="studyPrompts.length === 0" class="text-xs text-gray-400 mt-1">暂无学习资料类型的提示词，请先在「AI提示词」管理中创建</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">4. 填写基本信息</label>
        <div class="space-y-3 max-w-md">
          <div>
            <label class="block text-xs text-gray-500 mb-1">名称 <span class="text-red-500">*</span></label>
            <input v-model="formName" required class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" placeholder="学习资料名称" />
          </div>
          <div>
            <label class="block text-xs text-gray-500 mb-1">描述</label>
            <textarea v-model="formDesc" rows="3" class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400" placeholder="学习资料简要描述"></textarea>
          </div>
        </div>
      </div>

      <div class="flex items-center gap-3 pt-2">
        <button @click="confirmGenerate = true" :disabled="!canGenerate || generating"
          class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition">
          {{ generating ? '正在生成...' : '生成学习资料' }}
        </button>
        <span v-if="generating" class="inline-block w-4 h-4 border-2 border-primary-400 border-t-transparent rounded-full animate-spin"></span>
      </div>
    </div>

    <div v-if="message" class="mt-4 px-4 py-3 rounded-xl text-sm" :class="msgClass">{{ message }}</div>

    <ConfirmModal :show="confirmGenerate" title="确认生成" message="将调用 AI 生成完整的学习资料，可能需要 1-2 分钟，确认继续？" @confirm="doGenerate" @cancel="confirmGenerate = false" />

    <div v-if="generating" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/60">
      <div class="bg-white rounded-2xl shadow-xl px-8 py-6 text-center">
        <div class="inline-block w-8 h-8 border-4 border-primary-400 border-t-transparent rounded-full animate-spin mb-4"></div>
        <p class="text-sm text-gray-700 font-medium">正在生成学习资料，AI 生成可能需要 1-2 分钟，请稍候...</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";

definePageMeta({ middleware: ["auth", "teacher"] });

const { $api } = useNuxtApp();
const router = useRouter();

const libraries = ref([]);
const selectedLibraryId = ref(null);
const libraryDocs = ref([]);
const selectedDocs = ref([]);
const studyPrompts = ref([]);
const selectedPromptId = ref(null);
const formName = ref("");
const formDesc = ref("");
const generating = ref(false);
const confirmGenerate = ref(false);
const message = ref("");
const msgType = ref("success");

const canGenerate = computed(() => selectedLibraryId.value && selectedPromptId.value && formName.value.trim());
const msgClass = computed(() => msgType.value === "success" ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200");

async function fetchLibraries() {
  try {
    const res = await $api.get("/libraries");
    libraries.value = res.data.data;
  } catch {}
}

async function onLibraryChange() {
  selectedDocs.value = [];
  libraryDocs.value = [];
  if (!selectedLibraryId.value) return;
  try {
    const res = await $api.get(`/libraries/${selectedLibraryId.value}/documents`);
    libraryDocs.value = res.data.data.items;
  } catch {}
}

async function fetchStudyPrompts() {
  try {
    const res = await $api.get("/ai-prompts", { params: { type: "study" } });
    studyPrompts.value = res.data.data;
  } catch {}
}

function toggleSelectAll() {
  if (selectedDocs.value.length === libraryDocs.value.length) {
    selectedDocs.value = [];
  } else {
    selectedDocs.value = libraryDocs.value.map((d) => d.filename);
  }
}

async function doGenerate() {
  confirmGenerate.value = false;
  generating.value = true;
  try {
    const body = {
      name: formName.value.trim(),
      description: formDesc.value,
      library_id: selectedLibraryId.value,
      document_names: selectedDocs.value.length > 0 ? selectedDocs.value : [],
      prompt_id: selectedPromptId.value,
    };
    const res = await $api.post("/study-materials/generate", body);
    pollJob(res.data.data.job_id);
  } catch (e) {
    showMessage(e.response?.data?.detail || "生成失败", "error");
    generating.value = false;
  }
}

let pollTimer = null;
async function pollJob(jobId) {
  pollTimer = setInterval(async () => {
    try {
      const r = await $api.get(`/study-materials/generate/${jobId}`);
      const job = r.data.data;
      if (job.status === "done") {
        clearInterval(pollTimer);
        generating.value = false;
        showMessage("生成成功", "success");
        setTimeout(() => { router.push("/admin/study-materials"); }, 500);
      } else if (job.status === "failed") {
        clearInterval(pollTimer);
        generating.value = false;
        showMessage(job.error || "生成失败", "error");
      }
    } catch {
      clearInterval(pollTimer);
      generating.value = false;
      showMessage("生成状态查询失败", "error");
    }
  }, 3000);
}

function showMessage(msg, type) {
  message.value = msg;
  msgType.value = type;
  setTimeout(() => { message.value = ""; }, 5000);
}

fetchLibraries();
fetchStudyPrompts();
</script>
