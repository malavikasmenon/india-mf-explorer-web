<script setup lang="ts">
/**
 * CodeMirror 6 with the SQL language, its completion schema fed from the data
 * dictionary — so autocomplete knows the real tables and columns rather than a
 * hardcoded list, and stays correct as the dataset grows.
 *
 * The editor never rewrites what is typed. No injected LIMIT, no reformatting:
 * what runs is what is on screen.
 */
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { EditorState, type Extension } from '@codemirror/state';
import { EditorView, keymap, lineNumbers } from '@codemirror/view';
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands';
import { autocompletion, completionKeymap } from '@codemirror/autocomplete';
import { HighlightStyle, syntaxHighlighting } from '@codemirror/language';
import { tags } from '@lezer/highlight';
import { PostgreSQL, sql } from '@codemirror/lang-sql';

const props = defineProps<{
  modelValue: string;
  schema: Record<string, string[]>;
  running: boolean;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: string];
  run: [];
}>();

const host = ref<HTMLDivElement | null>(null);
let view: EditorView | null = null;

// Matches the wireframe's SQL block: keywords ochre, strings green, comments
// muted italic. Driven by CSS variables so dark mode comes along for free.
const highlight = HighlightStyle.define([
  { tag: tags.keyword, color: 'var(--accent)', fontWeight: '600' },
  { tag: [tags.string, tags.special(tags.string)], color: 'var(--pos)' },
  { tag: [tags.comment, tags.lineComment, tags.blockComment], color: 'var(--muted)', fontStyle: 'italic' },
  { tag: [tags.number, tags.bool, tags.null], color: 'var(--pos)' },
  { tag: tags.operator, color: 'var(--muted)' },
  { tag: [tags.function(tags.variableName), tags.standard(tags.variableName)], color: 'var(--ink)' },
]);

const theme = EditorView.theme({
  '&': { fontSize: '12.5px', backgroundColor: 'var(--surface)', color: 'var(--ink)' },
  '&.cm-focused': { outline: 'none' },
  '.cm-scroller': { fontFamily: 'var(--mono)', lineHeight: '1.65' },
  '.cm-content': { padding: '12px 0' },
  '.cm-gutters': {
    backgroundColor: 'var(--surface)',
    border: 'none',
    color: 'var(--line)',
    paddingRight: '10px',
    paddingLeft: '4px',
  },
  '.cm-activeLine': { backgroundColor: 'transparent' },
  '.cm-activeLineGutter': { backgroundColor: 'transparent', color: 'var(--muted)' },
  '.cm-cursor': { borderLeftColor: 'var(--accent)', borderLeftWidth: '2px' },
  '.cm-selectionBackground, ::selection': { backgroundColor: 'var(--accent-soft) !important' },
  '.cm-tooltip': {
    backgroundColor: 'var(--surface)',
    border: '1px solid var(--line)',
    borderRadius: '3px',
    fontFamily: 'var(--mono)',
    fontSize: '11.5px',
  },
  '.cm-tooltip-autocomplete ul li[aria-selected]': {
    backgroundColor: 'var(--accent-soft)',
    color: 'var(--accent)',
  },
});

function extensions(): Extension[] {
  return [
    lineNumbers(),
    history(),
    syntaxHighlighting(highlight, { fallback: true }),
    autocompletion(),
    // DuckDB has no dedicated CodeMirror dialect; Postgres is the closest fit
    // and DuckDB deliberately tracks Postgres syntax.
    sql({ dialect: PostgreSQL, schema: props.schema }),
    keymap.of([
      // Ahead of the defaults, so Mod-Enter runs rather than inserting a newline.
      { key: 'Mod-Enter', preventDefault: true, run: () => (emit('run'), true) },
      ...completionKeymap,
      ...historyKeymap,
      ...defaultKeymap,
    ]),
    theme,
    EditorView.lineWrapping,
    EditorView.updateListener.of((update) => {
      if (update.docChanged) emit('update:modelValue', update.state.doc.toString());
    }),
  ];
}

onMounted(() => {
  view = new EditorView({
    state: EditorState.create({ doc: props.modelValue, extensions: extensions() }),
    parent: host.value!,
  });
});

// The schema arrives with the manifest, after mount.
watch(
  () => props.schema,
  () => {
    if (!view) return;
    view.setState(
      EditorState.create({ doc: view.state.doc.toString(), extensions: extensions() }),
    );
  },
);

// Selecting an example replaces the document wholesale.
watch(
  () => props.modelValue,
  (next) => {
    if (view && next !== view.state.doc.toString()) {
      view.dispatch({
        changes: { from: 0, to: view.state.doc.length, insert: next },
      });
    }
  },
);

onBeforeUnmount(() => view?.destroy());

function insertAtCursor(text: string) {
  if (!view) return;
  const { from, to } = view.state.selection.main;
  view.dispatch({
    changes: { from, to, insert: text },
    selection: { anchor: from + text.length },
  });
  view.focus();
}

defineExpose({ insertAtCursor });
</script>

<template>
  <section class="panel">
    <div class="panel-head">
      <p class="label">Query editor</p>
      <p class="hint mono">DuckDB-WASM · runs in your browser · read-only</p>
    </div>

    <div ref="host" class="host"></div>

    <div class="foot">
      <button class="run" type="button" :disabled="running" @click="emit('run')">
        {{ running ? 'Running…' : 'Run' }}
      </button>
      <span class="kbd mono">⌘ / Ctrl + ↵</span>
    </div>
  </section>
</template>

<style scoped>
.hint {
  font-size: 10.5px;
  color: var(--muted);
  margin: 0;
}

.host {
  max-height: 210px;
  min-height: 110px;
  overflow: auto;
}

.foot {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 15px;
  border-top: 1px solid var(--line);
}

.run {
  font-family: var(--mono);
  font-size: 11.5px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 600;
  padding: 8px 24px;
  border: none;
  border-radius: 3px;
  background: var(--accent);
  color: var(--on-accent);
}

.run:hover:not(:disabled) {
  filter: brightness(1.08);
}

.run:disabled {
  opacity: 0.55;
  cursor: default;
}

.kbd {
  font-size: 10.5px;
  color: var(--muted);
}
</style>
