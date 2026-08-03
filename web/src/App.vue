<script setup lang="ts">
/**
 * The workbench shell: top bar, dictionary rail, composer, results, footer.
 *
 * Boot order matters — the manifest is fetched first, then the engine registers
 * a view per table it describes. Nothing here knows what those tables are.
 */
import { computed, onMounted, ref } from 'vue';
import SchemaRail from './components/SchemaRail.vue';
import SqlEditor from './components/SqlEditor.vue';
import ExampleQueries from './components/ExampleQueries.vue';
import ResultsGrid from './components/ResultsGrid.vue';
import {
  completionSchema,
  fetchManifest,
  type Manifest,
  type TableExample,
} from './catalog';
import { initDuckDB, runQuery, type QueryResult } from './duckdb';

const manifest = ref<Manifest | null>(null);
const booting = ref(true);
const bootError = ref<string | null>(null);

const sql = ref('');
const result = ref<QueryResult | null>(null);
const error = ref<string | null>(null);
const running = ref(false);
const activeExample = ref<string | null>(null);

const editor = ref<InstanceType<typeof SqlEditor> | null>(null);
const railOpen = ref(false);

const schema = computed(() => (manifest.value ? completionSchema(manifest.value) : {}));

const examples = computed(() => manifest.value?.tables.flatMap((t) => t.examples ?? []) ?? []);

/** Headline figures for the top bar, derived rather than stated. */
const stats = computed(() => {
  const tables = manifest.value?.tables ?? [];
  if (!tables.length) return [];
  const rows = tables.reduce((sum, t) => sum + t.row_count, 0);
  const retrieved = tables.find((t) => t.source?.retrieved_at)?.source?.retrieved_at;
  return [
    { k: 'Tables', v: String(tables.length) },
    { k: 'Rows', v: rows.toLocaleString() },
    ...(retrieved ? [{ k: 'Updated', v: retrieved.slice(0, 10) }] : []),
  ];
});

const sourceUrl = computed(
  () => manifest.value?.tables.find((t) => t.source?.source_url)?.source?.source_url ?? null,
);

onMounted(async () => {
  try {
    const loaded = await fetchManifest();
    await initDuckDB(loaded);
    manifest.value = loaded;

    const first = loaded.tables.flatMap((t) => t.examples ?? [])[0];
    if (first) {
      sql.value = first.sql;
      activeExample.value = first.label;
    } else {
      const table = [...loaded.tables].sort((a, b) => b.row_count - a.row_count)[0];
      sql.value = table ? `SELECT *\nFROM ${table.name}\nLIMIT 100` : 'SELECT 1';
    }

    booting.value = false;
    await run();
  } catch (err) {
    bootError.value = err instanceof Error ? err.message : String(err);
    booting.value = false;
  }
});

/** Clearing drops the example highlight too — nothing on screen came from it now. */
function clearEditor() {
  sql.value = '';
  activeExample.value = null;
}

function pick(example: TableExample) {
  sql.value = example.sql;
  activeExample.value = example.label;
  run();
}

async function run() {
  if (running.value || !sql.value.trim()) return;
  running.value = true;
  error.value = null;
  try {
    result.value = await runQuery(sql.value);
  } catch (err) {
    // Surfaced verbatim; DuckDB's own message is more useful than ours.
    error.value = err instanceof Error ? err.message : String(err);
    result.value = null;
  } finally {
    running.value = false;
  }
}
</script>

<template>
  <header class="topbar">
    <div class="brand">
      <h1 class="wordmark">OPEN <span>INDIAN</span> FUND DATA</h1>
      <p class="strap">Skip the ETL &amp; start at the question.</p>
    </div>
    <div class="stats">
      <span v-for="s in stats" :key="s.k">{{ s.k }} <b>{{ s.v }}</b></span>
    </div>
    <button class="rail-toggle" type="button" @click="railOpen = !railOpen">
      {{ railOpen ? '✕' : '☰' }} schema
    </button>
  </header>

  <div class="shell">
    <div class="rail-slot" :class="{ open: railOpen }">
      <SchemaRail
        v-if="manifest"
        :tables="manifest.tables"
        @insert="editor?.insertAtCursor($event)"
      />
    </div>

    <main class="main">
      <div v-if="booting" class="boot panel">
        <p class="mono">Starting the query engine…</p>
        <p class="boot-note">DuckDB is loading into this tab. Nothing is sent to a server.</p>
      </div>

      <div v-else-if="bootError" class="boot panel bad">
        <p class="label err">Could not start</p>
        <pre class="mono">{{ bootError }}</pre>
      </div>

      <template v-else>
        <SqlEditor
          ref="editor"
          v-model="sql"
          :schema="schema"
          :running="running"
          @run="run"
          @clear="clearEditor"
        />
        <ExampleQueries :examples="examples" :active="activeExample" @pick="pick" />
        <ResultsGrid :result="result" :error="error" :running="running" />
      </template>
    </main>
  </div>

  <footer class="footer">
    <div class="foot-col">
      <p class="label">Source</p>
      <p>
        Published daily by
        <a v-if="sourceUrl" :href="sourceUrl" target="_blank" rel="noopener">AMFI</a>
        <span v-else>AMFI</span>
        under SEBI's disclosure mandate. Every column is stored exactly as published.
      </p>
    </div>
    <div class="foot-col">
      <p class="label">Not financial advice</p>
      <p>
        A data tool. It describes what funds are and what they have returned, and shows
        where every number came from. It does not recommend investments.
      </p>
    </div>
  </footer>
</template>

<style scoped>
.topbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 22px;
  padding: 16px 26px;
  border-bottom: 1px solid var(--line);
  background: var(--surface);
}

/* Name and strapline stack, so the strapline reads as a subtitle rather than
   competing with the wordmark across the bar. */
.brand {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.wordmark {
  font-family: var(--mono);
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.02em;
  margin: 0;
}

.wordmark span {
  color: var(--accent);
}

.strap {
  margin: 0;
  font-size: 12.5px;
  color: var(--muted);
}

.stats {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 18px;
  margin-left: auto;
  font-family: var(--mono);
  font-size: 11px;
  color: var(--muted);
}

.stats b {
  color: var(--ink);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.shell {
  display: grid;
  grid-template-columns: var(--rail) minmax(0, 1fr);
  align-items: stretch;
  /* Absorbs the leftover viewport, which also carries the rail's divider all
     the way down to the footer rather than stopping where the content ends. */
  flex: 1;
}

/* The divider belongs to the full-height grid cell, not to the rail's content —
   on the content it stops wherever the field list happens to end. */
.rail-slot {
  border-right: 1px solid var(--line);
}

.main {
  padding: 22px 26px 40px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-width: 0;
}

.boot {
  display: grid;
  place-items: center;
  gap: 6px;
  padding: 56px 24px;
  text-align: center;
  color: var(--muted);
  font-size: 13px;
}

.boot-note {
  margin: 0;
  font-size: 11.5px;
}

.boot.bad {
  place-items: start;
  text-align: left;
}

.boot pre {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--neg);
  white-space: pre-wrap;
}

.err {
  color: var(--neg);
}

.footer {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 26px;
  padding: 26px;
  border-top: 1px solid var(--line);
  background: var(--surface);
  font-size: 12px;
  color: var(--muted);
}

.foot-col p {
  margin: 6px 0 0;
  line-height: 1.5;
}

.foot-col a {
  color: var(--accent);
}

.rail-toggle {
  display: none;
}

@media (max-width: 900px) {
  .shell {
    grid-template-columns: minmax(0, 1fr);
  }

  .stats {
    margin-left: 0;
  }

  .rail-toggle {
    display: block;
    margin-left: auto;
    padding: 5px 11px;
    background: var(--surface-2);
    border: 1px solid var(--line);
    border-radius: 3px;
    font-family: var(--mono);
    font-size: 11px;
  }

  /* Collapsed by default on a phone: the grid needs the whole width. */
  .rail-slot {
    display: none;
    border-right: none;
  }

  .rail-slot.open {
    display: block;
  }

  .main {
    padding: 16px 14px 32px;
  }
}
</style>
