<template>
  <ClientOnly>
    <div ref="hostRef" class="absolute inset-0"></div>
    <template #fallback>
      <div class="absolute inset-0 overflow-auto p-3 text-sm font-mono whitespace-pre-wrap text-gray-700 bg-gray-50">{{ content }}</div>
    </template>
  </ClientOnly>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from "vue";
import { EditorView } from "@codemirror/view";
import { EditorState, StateEffect, StateField, RangeSetBuilder } from "@codemirror/state";
import { Decoration } from "@codemirror/view";
import { diffWordsWithSpace } from "diff";
import { logger } from "@/utils/logger";

const props = defineProps({
  content: { type: String, default: "" },
  compareTo: { type: String, default: "" }
});

const emit = defineEmits(["editorReady"]);

const hostRef = ref(null);
let editorView = null;
let decorationsTimer = null;
let resizeObserver = null;

const setDecorations = StateEffect.define();

function buildRemovedDecorations(origin, preview) {
  if (!origin || !preview) return Decoration.none;
  const diffs = diffWordsWithSpace(origin, preview);
  const builder = new RangeSetBuilder();
  let pos = 0;
  for (const part of diffs) {
    const len = part.value.length;
    if (part.removed) {
      builder.add(pos, pos + len, Decoration.mark({ attributes: { class: "cm-diff-removed" } }));
      pos += len;
    } else if (part.added) {
      // skip - added words are not in origin
    } else {
      pos += len;
    }
  }
  return builder.finish();
}

const decorationField = StateField.define({
  create() { return Decoration.none; },
  update(_decs, tr) {
    for (const e of tr.effects) if (e.is(setDecorations)) return e.value;
    return Decoration.none;
  },
  provide: (f) => EditorView.decorations.from(f)
});

function updateDiffDecorations() {
  if (!editorView) return;
  const decs = buildRemovedDecorations(props.content, props.compareTo);
  editorView.dispatch({ effects: setDecorations.of(decs) });
}

const readonlyTheme = EditorView.theme({
  "&": { backgroundColor: "rgb(249 250 251)", height: "100%", minHeight: "100%" },
  ".cm-content": {
    padding: "0.75rem",
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
    fontSize: "0.875rem",
    lineHeight: "1.5"
  },
  ".cm-scroller": { overflow: "auto", height: "100%", minHeight: "100%" }
});

onMounted(() => {
  nextTick(() => {
  try {
    const state = EditorState.create({
      doc: props.content,
      extensions: [
        EditorView.editable.of(false),
        EditorView.lineWrapping,
        readonlyTheme,
        decorationField
      ]
    });
    editorView = new EditorView({ state, parent: hostRef.value });
    updateDiffDecorations();

    nextTick(() => {
      if (editorView) editorView.requestMeasure();
    });
    resizeObserver = new ResizeObserver(() => {
      if (editorView) editorView.requestMeasure();
    });
    if (hostRef.value) resizeObserver.observe(hostRef.value);

    emit("editorReady", editorView);
  } catch (err) {
    logger.error("[ReadonlyMarkdown]", "init FAILED", { error: String(err) });
    if (hostRef.value) {
      hostRef.value.innerHTML = `<div style="color:red;padding:16px;font-family:monospace">[ReadonlyMarkdown] 初始化失败: ${String(err)}</div>`;
    }
  }
  });
});

onUnmounted(() => {
  clearTimeout(decorationsTimer);
  resizeObserver?.disconnect();
  resizeObserver = null;
  editorView?.destroy();
  editorView = null;
});

watch(() => props.content, (newVal) => {
  if (!editorView) return;
  if (newVal !== editorView.state.doc.toString()) {
    editorView.dispatch({
      changes: { from: 0, to: editorView.state.doc.length, insert: newVal }
    });
    updateDiffDecorations();
    editorView.requestMeasure();
  }
});

watch(() => props.compareTo, () => {
  clearTimeout(decorationsTimer);
  decorationsTimer = setTimeout(() => {
    updateDiffDecorations();
  }, 80);
});

function getEditor() {
  return editorView;
}

function setScrollTop(t) {
  if (editorView) editorView.scrollDOM.scrollTop = t;
}

defineExpose({ getEditor, setScrollTop });
</script>
