<template>
  <div v-if="stageData">
    <div class="mb-4">
      <NuxtLink to="/admin/approvals" class="text-sm text-primary-600 hover:underline">&larr; 返回审批列表</NuxtLink>
    </div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-4 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <h2 class="text-lg font-bold text-gray-900">{{ stageData.original_filename }}</h2>
        <span class="text-xs px-2 py-0.5 rounded-full" :class="typeBadge(stageData.file_type)">{{ typeLabel(stageData.file_type) }}</span>
        <span class="text-xs px-2 py-0.5 rounded-full" :class="statusBadge(stageData.status)">{{ statusLabel(stageData.status) }}</span>
      </div>
      <div class="flex items-center gap-2">
        <label class="text-sm text-gray-600">入库名称：</label>
        <input v-model="newName" @blur="saveNewName" class="px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400 w-64" />
      </div>
    </div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden mb-4">
      <div class="flex border-b border-gray-200">
        <div class="px-4 py-3 text-sm font-medium text-gray-400">新文档</div>
        <button v-for="(tab, idx) in tabs" :key="idx" @click="activeTab = idx"
          class="px-4 py-3 text-sm font-medium transition border-b-2 -mb-px"
          :class="activeTab === idx ? 'text-primary-700 border-primary-600' : 'text-gray-500 border-transparent hover:text-gray-700'">
          {{ tab }}
        </button>
      </div>

      <div class="p-6">
        <!-- Tab: Content Diff -->
        <div v-if="activeTab === 0">
          <div class="mb-4">
            <button @click="handleDiffConfirm" :disabled="diffLoading"
              class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50">
              {{ diffLoading ? '正在生成...' : (contentDiff.new.length || contentDiff.conflict.length ? '重新生成内容差异' : '生成内容差异') }}
            </button>
          </div>
          <div v-if="diffLoading" class="flex items-center gap-2 text-sm text-gray-500 mb-4">
            <span class="inline-block w-4 h-4 border-2 border-primary-400 border-t-transparent rounded-full animate-spin"></span>
            正在调用 AI 分析文档差异，请稍候...
          </div>

          <div v-if="contentDiff.new.length > 0 || contentDiff.conflict.length > 0" class="space-y-6">
            <div v-if="contentDiff.new.length">
              <h4 class="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-green-500"></span> 新文档中的全新内容
              </h4>
              <div class="space-y-2">
                <div v-for="(item, i) in contentDiff.new" :key="'n'+i" class="p-3 bg-green-50 border border-green-100 rounded-lg text-sm text-gray-800">{{ item }}</div>
              </div>
            </div>
            <div v-if="contentDiff.conflict.length">
              <h4 class="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-amber-500"></span> 与已有文档冲突的内容
              </h4>
              <div class="space-y-3">
                <div v-for="(item, i) in contentDiff.conflict" :key="'c'+i" class="border border-amber-200 rounded-lg overflow-hidden">
                  <div class="bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-800">新文档内容</div>
                  <div class="p-3 text-sm text-gray-800">{{ item.new }}</div>
                  <div class="bg-gray-50 px-3 py-1.5 text-xs font-medium text-gray-600">冲突文档: {{ item.old_doc_name }}</div>
                  <div class="p-3 text-sm text-gray-600">{{ item.old }}</div>
                </div>
              </div>
            </div>
          </div>
          <div v-else-if="!diffLoading" class="text-sm text-gray-400 py-12 text-center">点击"生成内容差异"使用 AI 分析新旧文档内容</div>
          <div v-if="contentDiff.new.length > 0 || contentDiff.conflict.length > 0" class="mt-6">
            <button @click="confirmDiff" class="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700">确认，进入下一步</button>
          </div>
        </div>

        <!-- Tab: Content Choice -->
        <div v-if="activeTab === 1">
          <div class="grid grid-cols-3 gap-3 mb-6">
            <button @click="selectChoice('新增')"
              class="p-4 rounded-xl border-2 text-center transition"
              :class="contentChoice === '新增' ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-gray-300'">
              <div class="font-semibold text-sm mb-1" :class="contentChoice === '新增' ? 'text-primary-700' : 'text-gray-700'">新增</div>
            </button>
            <button @click="selectChoice('替换整个文档库')" :disabled="libraryDocs.length === 0"
              class="p-4 rounded-xl border-2 text-center transition disabled:opacity-40 disabled:cursor-not-allowed"
              :class="contentChoice === '替换整个文档库' ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-gray-300'">
              <div class="font-semibold text-sm mb-1" :class="contentChoice === '替换整个文档库' ? 'text-primary-700' : 'text-gray-700'">替换整个文档库</div>
            </button>
            <button @click="selectChoice('替换部分文档')" :disabled="libraryDocs.length === 0"
              class="p-4 rounded-xl border-2 text-center transition disabled:opacity-40 disabled:cursor-not-allowed"
              :class="contentChoice === '替换部分文档' ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-gray-300'">
              <div class="font-semibold text-sm mb-1" :class="contentChoice === '替换部分文档' ? 'text-primary-700' : 'text-gray-700'">替换部分文档</div>
            </button>
          </div>
          <div class="p-4 bg-blue-50 border border-blue-100 rounded-lg text-sm text-blue-800 mb-4">
            新文档「{{ newName }}」将被添加进文档库
            <span v-if="contentChoice === '替换整个文档库'">，所有老文档将被删除</span>
            <span v-else-if="contentChoice === '替换部分文档'">，选中的老文档会被删除</span>
          </div>

          <div v-if="contentChoice === '替换部分文档' && libraryDocs.length > 0">
            <h4 class="text-sm font-semibold text-gray-700 mb-2">选择要替换（删除）的文档：</h4>
            <div class="space-y-1 max-h-60 overflow-y-auto">
              <label v-for="doc in libraryDocs" :key="doc.id" class="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-50 cursor-pointer">
                <input type="checkbox" :value="doc.filename" v-model="replaceDocs" class="w-4 h-4 text-primary-600 border-gray-300 rounded" />
                <span class="text-sm text-gray-700">{{ doc.filename }}</span>
              </label>
            </div>
          </div>
          <div v-if="contentChoice === '替换整个文档库' && libraryDocs.length > 0" class="text-sm text-red-600 mt-2">
            将删除以下文档：
            <ul class="list-disc list-inside mt-1 text-gray-600">
              <li v-for="doc in libraryDocs" :key="doc.id">{{ doc.filename }}</li>
            </ul>
          </div>
          <button @click="saveContentChoice" class="mt-4 px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700">确认，进入下一步</button>
        </div>

        <!-- Tab: Rewrite -->
        <div v-if="activeTab === 2">
          <div class="flex items-center gap-3 mb-4">
            <select v-model="rewriteMethod" class="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400">
              <option value="keep">保持不变</option>
              <option value="grammar">仅文字和语法错误改写</option>
              <option value="" disabled>──────</option>
              <option v-for="s in rewriteStyles" :key="s.id" :value="'style_'+s.id">{{ s.name }}</option>
            </select>
            <button @click="handleRewriteConfirm" :disabled="rewriteLoading"
              class="px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50">
              {{ rewriteLoading ? '改写中...' : '改写' }}
            </button>
            <span v-if="rewriteLoading" class="inline-block w-4 h-4 border-2 border-primary-400 border-t-transparent rounded-full animate-spin ml-2"></span>
          </div>

          <div class="flex gap-0 border border-gray-200 rounded-lg overflow-hidden" style="height: calc(100vh - 360px); min-height: 300px;">
            <div class="flex-1 flex flex-col">
              <div class="px-3 py-1.5 bg-gray-50 border-b border-gray-200 text-xs font-medium text-gray-600">原文 (origin.md)</div>
              <div class="flex-1 relative overflow-hidden bg-gray-50">
                <ReadonlyMarkdown :content="originContent" :compareTo="previewContent" @editorReady="onLeftEditorReady" />
              </div>
            </div>
            <div class="flex-1 flex flex-col border-l border-gray-200">
              <div class="px-3 py-1.5 bg-gray-50 border-b border-gray-200 text-xs font-medium text-gray-600">改写结果 (preview.md)</div>
              <div class="flex-1 relative overflow-hidden">
                <RewriteDiffEditor v-model="previewContent" :origin="originContent" @editorReady="onRightEditorReady" />
              </div>
            </div>
          </div>
          <button @click="savePreviewContent" class="mt-4 px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700">确认，进入下一步</button>
        </div>

        <!-- Tab: Preview & Complete -->
        <div v-if="activeTab === 3">
          <div class="mb-4 p-4 bg-blue-50 border border-blue-100 rounded-lg text-sm text-blue-800">
            <span class="font-medium">处理方式：</span>{{ contentChoice === '新增' ? '新增文档至文档库' : contentChoice === '替换整个文档库' ? '替换整个文档库（所有旧文档将被删除）' : '替换部分文档' }}
            <div v-if="contentChoice === '替换部分文档' && replaceDocs.length > 0" class="mt-2">
              <span class="font-medium">将被替换的文档：</span>
              <span v-for="(fn, i) in replaceDocs" :key="i" class="ml-1 text-red-600">{{ fn }}{{ i < replaceDocs.length - 1 ? '、' : '' }}</span>
            </div>
          </div>

          <div class="border border-gray-200 rounded-lg overflow-hidden" style="height: calc(100vh - 400px);">
            <div class="px-3 py-1.5 bg-gray-50 border-b border-gray-200 text-xs font-medium text-gray-600">最终预览 (preview.md)</div>
            <div class="overflow-auto p-6 h-full markdown-body" v-html="renderedPreview"></div>
          </div>

          <div class="mt-4 flex gap-3">
            <button @click="confirmOpen = true" class="px-6 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 font-medium">确认入库</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="message" class="mt-4 px-4 py-3 rounded-xl text-sm" :class="msgClass">{{ message }}</div>

    <ConfirmModal :show="diffConfirmOpen" title="生成内容差异" message="将调用 AI 分析新文档与现有文档库的差异，可能需要几十秒时间，确认继续？" @confirm="generateDiff" @cancel="diffConfirmOpen = false" />
    <ConfirmModal :show="rewriteConfirmOpen" title="执行改写" message="继续操作将丢弃之前的改写内容，确认继续？" @confirm="executeRewrite" @cancel="rewriteConfirmOpen = false" />
    <ConfirmModal :show="confirmOpen" title="确认入库" message="确认后将执行以下操作：备份文档库 → 处理文档替换 → 将新文档入库。操作不可逆，确认继续？" variant="danger" confirmText="确认入库" @confirm="executeConfirm" @cancel="confirmOpen = false" />
  </div>
  <div v-else class="text-center text-gray-400 py-20">加载中...</div>
</template>

<script setup>
import { ref, computed, nextTick } from "vue";
import { marked } from "marked";
import hljs from "highlight.js";
import "highlight.js/styles/github.css";

marked.setOptions({
  highlight: function (code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value;
    }
    return hljs.highlightAuto(code).value;
  },
});

definePageMeta({ middleware: ["auth", "teacher"] });

const { $api } = useNuxtApp();
const route = useRoute();

const approvalId = computed(() => route.params.id);
const tabs = ["内容差异比较", "内容选择", "文字改写", "预览并完成"];

const stageData = ref(null);
const activeTab = ref(0);
const newName = ref("");
const contentChoice = ref("新增");
const replaceDocs = ref([]);
const contentDiff = ref({ new: [], conflict: [] });
const previewContent = ref("");
const originContent = ref("");
const libraryDocs = ref([]);
const rewriteStyles = ref([]);
const rewriteMethod = ref("keep");
const message = ref("");
const msgType = ref("success");

const diffLoading = ref(false);
const diffConfirmOpen = ref(false);
const rewriteLoading = ref(false);
const rewriteConfirmOpen = ref(false);
const confirmOpen = ref(false);

const leftEditorView = ref(null);
const rightEditorView = ref(null);
let leftScrollSyncing = false;
let rightScrollSyncing = false;

const msgClass = computed(() => msgType.value === "success" ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200");

const renderedPreview = computed(() => marked(previewContent.value));

function onLeftEditorReady(view) {
  leftEditorView.value = view;
  view.scrollDOM.addEventListener("scroll", onLeftScroll);
}

function onRightEditorReady(view) {
  rightEditorView.value = view;
  view.scrollDOM.addEventListener("scroll", onRightScroll);
}

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

async function fetchDetail() {
  try {
    const res = await $api.get(`/approvals/${approvalId.value}`);
    const d = res.data.data;
    stageData.value = d;
    newName.value = d.approval.new_name || d.original_filename;
    contentChoice.value = d.approval.content_choice || "新增";
    replaceDocs.value = d.approval.replace_docs || [];
    contentDiff.value = d.approval.content_diff || { new: [], conflict: [] };
    previewContent.value = d.preview_content || "";
    originContent.value = d.origin_content || "";
    libraryDocs.value = d.library_documents || [];
  } catch (e) {
    showMessage("加载审批详情失败", "error");
  }
}

async function fetchRewriteStyles() {
  try {
    const res = await $api.get("/rewrite-styles");
    rewriteStyles.value = res.data.data;
  } catch {}
}

async function saveNewName() {
  if (!newName.value) return;
  try {
    await $api.put(`/approvals/${approvalId.value}/meta`, { new_name: newName.value });
  } catch {}
}

async function selectChoice(choice) {
  if (libraryDocs.value.length === 0 && choice !== "新增") return;
  contentChoice.value = choice;
  if (choice !== "替换部分文档") {
    replaceDocs.value = [];
  }
}

async function saveContentChoice() {
  try {
    await $api.put(`/approvals/${approvalId.value}/meta`, {
      content_choice: contentChoice.value,
      replace_docs: replaceDocs.value,
    });
    showMessage("已保存", "success");
    activeTab.value = 2;
  } catch (e) {
    showMessage(e.response?.data?.detail || "保存失败", "error");
  }
}

function confirmDiff() {
  activeTab.value = 1;
}

function handleDiffConfirm() {
  diffConfirmOpen.value = true;
}

async function generateDiff() {
  diffConfirmOpen.value = false;
  diffLoading.value = true;
  try {
    const res = await $api.post(`/approvals/${approvalId.value}/content-diff`);
    contentDiff.value = res.data.data;
    stageData.value.status = "content_review";
    showMessage("内容差异已生成", "success");
  } catch (e) {
    showMessage(e.response?.data?.detail || "生成差异失败", "error");
  } finally {
    diffLoading.value = false;
  }
}

function handleRewriteConfirm() {
  rewriteConfirmOpen.value = true;
}

async function executeRewrite() {
  rewriteConfirmOpen.value = false;
  rewriteLoading.value = true;
  try {
    let method = rewriteMethod.value;
    let styleId = null;
    if (method.startsWith("style_")) {
      styleId = parseInt(method.split("_")[1]);
      method = "style";
    }
    const body = { method };
    if (styleId) body.style_id = styleId;
    const res = await $api.post(`/approvals/${approvalId.value}/rewrite`, body);
    previewContent.value = res.data.data.content;
    stageData.value.status = "rewrite";
    showMessage("改写完成", "success");
    await nextTick();
    if (rightEditorView.value) rightEditorView.value.scrollDOM.scrollTop = 0;
  } catch (e) {
    showMessage(e.response?.data?.detail || "改写失败", "error");
  } finally {
    rewriteLoading.value = false;
  }
}

async function savePreviewContent() {
  try {
    await $api.put(`/approvals/${approvalId.value}/preview`, { content: previewContent.value });
    showMessage("已保存", "success");
    activeTab.value = 3;
  } catch (e) {
    showMessage(e.response?.data?.detail || "保存失败", "error");
  }
}

async function executeConfirm() {
  confirmOpen.value = false;
  try {
    await $api.post(`/approvals/${approvalId.value}/confirm`);
    showMessage("入库完成", "success");
    setTimeout(() => { navigateTo("/admin/approvals"); }, 500);
  } catch (e) {
    showMessage(e.response?.data?.detail || "入库失败", "error");
  }
}

function onLeftScroll() {
  if (leftScrollSyncing) return;
  rightScrollSyncing = true;
  if (rightEditorView.value && leftEditorView.value) {
    const ls = leftEditorView.value.scrollDOM;
    const rs = rightEditorView.value.scrollDOM;
    const ratio = ls.scrollTop / (ls.scrollHeight - ls.clientHeight);
    rs.scrollTop = ratio * (rs.scrollHeight - rs.clientHeight);
  }
  nextTick(() => { rightScrollSyncing = false; });
}

function onRightScroll() {
  if (rightScrollSyncing || rewriteMethod.value.startsWith("style_")) return;
  leftScrollSyncing = true;
  if (rightEditorView.value && leftEditorView.value) {
    const rs = rightEditorView.value.scrollDOM;
    const ls = leftEditorView.value.scrollDOM;
    const ratio = rs.scrollTop / (rs.scrollHeight - rs.clientHeight);
    ls.scrollTop = ratio * (ls.scrollHeight - ls.clientHeight);
  }
  nextTick(() => { leftScrollSyncing = false; });
}

function showMessage(msg, type) {
  message.value = msg;
  msgType.value = type;
  setTimeout(() => { message.value = ""; }, 3000);
}

fetchDetail();
fetchRewriteStyles();
</script>
