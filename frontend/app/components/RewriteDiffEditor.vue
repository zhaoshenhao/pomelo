<template>
  <ClientOnly>
    <div ref="hostRef" class="absolute inset-0"></div>
    <template #fallback>
      <div class="absolute inset-0 overflow-auto p-3 text-sm font-mono whitespace-pre-wrap text-gray-700">{{ modelValue }}</div>
    </template>
  </ClientOnly>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from "vue";
import { EditorView, keymap } from "@codemirror/view";
import { EditorState, StateEffect, StateField, RangeSetBuilder } from "@codemirror/state";
import { defaultKeymap } from "@codemirror/commands";
import { Decoration } from "@codemirror/view";
import { diffWordsWithSpace } from "diff";
import { logger } from "@/utils/logger";

const props = defineProps({
  origin: { type: String, default: "" },
  modelValue: { type: String, default: "" }
});

const emit = defineEmits(["update:modelValue", "editorReady"]);

const hostRef = ref(null);
let editorView = null;
let decorationsRaf = null;
let resizeObserver = null;

const setDecorations = StateEffect.define();

function buildDiffDecorations(origin, preview) {
  if (!origin || !preview) return Decoration.none;
  const diffs = diffWordsWithSpace(origin, preview);
  const builder = new RangeSetBuilder();
  let pos = 0;
  let prevRemoved = false;
  for (const part of diffs) {
    const len = part.value.length;
    if (part.added) {
      const cls = prevRemoved ? "cm-diff-modified" : "cm-diff-added";
      builder.add(pos, pos + len, Decoration.mark({ attributes: { class: cls } }));
      pos += len;
      prevRemoved = false;
    } else if (part.removed) {
      prevRemoved = true;
    } else {
      pos += len;
      prevRemoved = false;
    }
  }
  return builder.finish();
}

const decorationField = StateField.define({
  create() { return Decoration.none; },
  update(decs, tr) {
    for (const e of tr.effects) if (e.is(setDecorations)) return e.value;
    return decs.map(tr.changes);
  },
  provide: (f) => EditorView.decorations.from(f)
});

function updateDiffDecorations(view) {
  if (!view) return;
  const decs = buildDiffDecorations(props.origin, view.state.doc.toString());
  view.dispatch({ effects: setDecorations.of(decs) });
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

onMounted(() => {
  nextTick(() => {
  try {
    const updateListener = EditorView.updateListener.of((update) => {
      if (!update.docChanged) return;
      const newText = update.state.doc.toString();
      cancelAnimationFrame(decorationsRaf);
      decorationsRaf = requestAnimationFrame(() => {
        if (editorView) updateDiffDecorations(editorView);
      });
      if (newText !== props.modelValue) {
        emit("update:modelValue", newText);
      }
    });

    const state = EditorState.create({
      doc: props.modelValue,
      extensions: [
        EditorView.lineWrapping,
        keymap.of(defaultKeymap),
        editorTheme,
        decorationField,
        updateListener
      ]
    });

    editorView = new EditorView({ state, parent: hostRef.value });
    updateDiffDecorations(editorView);

    nextTick(() => {
      if (editorView) editorView.requestMeasure();
    });
    resizeObserver = new ResizeObserver(() => {
      if (editorView) editorView.requestMeasure();
    });
    if (hostRef.value) resizeObserver.observe(hostRef.value);

    emit("editorReady", editorView);
  } catch (err) {
    logger.error("[RewriteDiffEditor]", "init FAILED", { error: String(err) });
    if (hostRef.value) {
      hostRef.value.innerHTML = `<div style="color:red;padding:16px;font-family:monospace">[RewriteDiffEditor] 初始化失败: ${String(err)}</div>`;
    }
  }
  });
});

onUnmounted(() => {
  cancelAnimationFrame(decorationsRaf);
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
    updateDiffDecorations(editorView);
    editorView.requestMeasure();
  }
});

watch(() => props.origin, () => {
  if (editorView) {
    updateDiffDecorations(editorView);
    editorView.requestMeasure();
  }
});

function getEditor() {
  return editorView;
}

function setScrollTop(t) {
  if (editorView) editorView.scrollDOM.scrollTop = t;
}

defineExpose({ getEditor, setScrollTop });
</script>
