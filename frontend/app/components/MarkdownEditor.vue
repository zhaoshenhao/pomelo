<template>
  <div class="flex flex-col h-full">
    <div class="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-200 shrink-0">
      <span class="text-xs font-medium text-gray-600">{{ mode === "edit" ? "编辑" : "预览" }}</span>
      <button @click="toggleMode" class="text-xs px-3 py-1 rounded-md border border-gray-300 hover:bg-white transition">
        {{ mode === "edit" ? "切换至预览" : "切换至编辑" }}
      </button>
    </div>
    <div class="flex-1 relative overflow-hidden">
      <ClientOnly>
        <div ref="hostRef" v-show="mode === 'edit'" class="absolute inset-0"></div>
        <template #fallback>
          <div class="absolute inset-0 overflow-auto p-3 text-sm font-mono whitespace-pre-wrap text-gray-700">{{ modelValue }}</div>
        </template>
      </ClientOnly>
      <div v-show="mode === 'view'" class="absolute inset-0 overflow-auto p-4 markdown-body" v-html="renderedHtml"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from "vue";
import { EditorView, keymap } from "@codemirror/view";
import { EditorState } from "@codemirror/state";
import { markdown } from "@codemirror/lang-markdown";
import { syntaxHighlighting } from "@codemirror/language";
import { markdownHighlightStyle } from "@/utils/markdownHighlight";
import { defaultKeymap } from "@codemirror/commands";
import { marked } from "marked";
import { sanitizeHtml } from "@/utils/sanitize";

const props = defineProps({
  modelValue: { type: String, default: "" }
});

const emit = defineEmits(["update:modelValue"]);

const mode = ref("edit");
const hostRef = ref(null);
let editorView = null;
let resizeObserver = null;

const renderedHtml = computed(() => sanitizeHtml(marked(props.modelValue)));

function toggleMode() {
  mode.value = mode.value === "edit" ? "view" : "edit";
  nextTick(() => {
    if (editorView) editorView.requestMeasure();
  });
}

const editorTheme = EditorView.theme({
  "&": { backgroundColor: "transparent", height: "100%", minHeight: "100%" },
  ".cm-content": {
    padding: "0.75rem",
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
    fontSize: "0.875rem",
    lineHeight: "1.5"
  },
  ".cm-scroller": { overflow: "auto", height: "100%", minHeight: "100%" }
});

function initEditor() {
  try {
    const updateListener = EditorView.updateListener.of((update) => {
      if (!update.docChanged) return;
      const newText = update.state.doc.toString();
      if (newText !== props.modelValue) {
        emit("update:modelValue", newText);
      }
    });

    const state = EditorState.create({
      doc: props.modelValue,
      extensions: [
        markdown(),
        syntaxHighlighting(markdownHighlightStyle, { fallback: true }),
        EditorView.lineWrapping,
        keymap.of(defaultKeymap),
        editorTheme,
        updateListener
      ]
    });

    editorView = new EditorView({ state, parent: hostRef.value });
    editorView.requestMeasure();
  } catch (err) {
    if (hostRef.value) {
      hostRef.value.innerHTML = `<div style="color:red;padding:16px;font-family:monospace">编辑器初始化失败: ${String(err)}</div>`;
    }
  }
}

onMounted(() => {
  nextTick(() => {
    initEditor();
    nextTick(() => {
      if (editorView) editorView.requestMeasure();
    });
    resizeObserver = new ResizeObserver(() => {
      if (editorView) editorView.requestMeasure();
    });
    if (hostRef.value) resizeObserver.observe(hostRef.value);
  });
});

onUnmounted(() => {
  resizeObserver?.disconnect();
  resizeObserver = null;
  editorView?.destroy();
  editorView = null;
});

watch(() => props.modelValue, (newVal) => {
  if (!editorView) return;
  if (newVal !== editorView.state.doc.toString()) {
    editorView.dispatch({
      changes: { from: 0, to: editorView.state.doc.length, insert: newVal }
    });
  }
});

watch(mode, (newMode) => {
  if (newMode === "edit") {
    nextTick(() => {
      if (editorView) editorView.requestMeasure();
    });
  }
});

defineExpose({ getEditor: () => editorView });
</script>
