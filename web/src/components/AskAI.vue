<script setup lang="ts">
/**
 * Turns a plain-English question into a copy-paste prompt for the user's own
 * Claude — schema plus question, phrased so the reply is one runnable DuckDB
 * query. There is no key and no server call here: the model call happens in
 * a tab this app never sees, which is what keeps the app itself free to run.
 */
import { computed, ref } from 'vue';
import { describeSchemaForPrompt, type Manifest } from '../catalog';

const props = defineProps<{ manifest: Manifest }>();

const question = ref('');
const copied = ref(false);
let copiedTimer: ReturnType<typeof setTimeout> | undefined;

const prompt = computed(() => {
  const q = question.value.trim();
  return [
    'You are writing a DuckDB SQL query against the schema below.',
    '',
    describeSchemaForPrompt(props.manifest),
    '',
    `Question: ${q || '<your question here>'}`,
    '',
    'Reply with a single DuckDB SQL query that answers it — no explanation, no markdown fences.',
  ].join('\n');
});

async function copyPrompt() {
  await navigator.clipboard.writeText(prompt.value);
  copied.value = true;
  clearTimeout(copiedTimer);
  copiedTimer = setTimeout(() => (copied.value = false), 1600);
}
</script>

<template>
  <section class="panel ask">
    <div class="panel-head">
      <p class="label">Ask in plain English</p>
      <p class="hint mono">No account, no key — runs in your own Claude tab</p>
    </div>

    <div class="body">
      <textarea
        v-model="question"
        class="mono"
        rows="2"
        placeholder="e.g. which large-cap funds returned more than 15% last year?"
      ></textarea>

      <div class="actions">
        <button type="button" class="copy" :disabled="!question.trim()" @click="copyPrompt">
          {{ copied ? 'Copied ✓' : 'Copy prompt' }}
        </button>
        <a class="open" href="https://claude.ai/new" target="_blank" rel="noopener">Open Claude ↗</a>
        <span class="note">Paste the prompt in, then paste the SQL it gives back into the editor below.</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.hint {
  font-size: 10.5px;
  color: var(--muted);
  margin: 0;
}

.body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 15px 14px;
}

textarea {
  resize: vertical;
  min-height: 44px;
  padding: 9px 10px;
  border: 1px solid var(--line);
  border-radius: 3px;
  background: var(--bg);
  color: var(--ink);
  font-size: 12.5px;
  line-height: 1.5;
}

textarea:focus-visible {
  border-color: var(--accent);
}

.actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.copy {
  font-family: var(--mono);
  font-size: 11.5px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 600;
  padding: 8px 18px;
  border: none;
  border-radius: 3px;
  background: var(--accent);
  color: var(--on-accent);
}

.copy:hover:not(:disabled) {
  filter: brightness(1.08);
}

.copy:disabled {
  opacity: 0.55;
  cursor: default;
}

.open {
  font-family: var(--mono);
  font-size: 11.5px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 600;
  color: var(--accent);
  text-decoration: none;
}

.open:hover {
  text-decoration: underline;
}

.note {
  font-size: 11.5px;
  color: var(--muted);
}
</style>
