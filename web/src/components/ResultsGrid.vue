<script setup lang="ts">
/**
 * Results, in a panel whose head carries the run status — row count, timing, and
 * any error, verbatim.
 *
 * Columns come from the Arrow result schema, so any query shape renders. This is
 * not a view of one table; it is a view of whatever the last statement returned.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import {
  createColumnHelper,
  getCoreRowModel,
  getPaginationRowModel,
  useVueTable,
} from '@tanstack/vue-table';
import { exportQuery, type ExportFormat, type QueryResult } from '../duckdb';
import { MAX_RENDERED_ROWS } from '../config';

const props = defineProps<{
  result: QueryResult | null;
  error: string | null;
  running: boolean;
}>();

type Row = Record<string, unknown>;
const helper = createColumnHelper<Row>();

const columns = computed(() =>
  (props.result?.columns ?? []).map((column) =>
    helper.accessor((row) => row[column.name], {
      id: column.name,
      header: column.name,
      meta: { type: column.type },
    }),
  ),
);

const table = useVueTable({
  get data() {
    return props.result?.rows ?? [];
  },
  get columns() {
    return columns.value;
  },
  getCoreRowModel: getCoreRowModel(),
  getPaginationRowModel: getPaginationRowModel(),
  initialState: { pagination: { pageIndex: 0, pageSize: 25 } },
});

const NUMERIC = /^(TINYINT|SMALLINT|INTEGER|BIGINT|HUGEINT|U?[A-Z]*INT|FLOAT|DOUBLE|DECIMAL|REAL)/;

/**
 * Alignment is a property of the column, not of the individual value — deciding
 * it per cell lets a header sit left while its numbers sit right, and drops a
 * NULL in a numeric column onto the wrong edge.
 */
function isNumeric(type: string): boolean {
  return NUMERIC.test(type);
}

/**
 * NULL and empty string are different facts here — one means AMFI published
 * nothing, the other means it published a blank — so they must never render
 * identically. BIGINT arrives as a JS BigInt, which stringifies to
 * "[object Object]" through the default path and throws in JSON.stringify.
 */
function render(value: unknown): { text: string; isNull: boolean } {
  if (value === null || value === undefined) return { text: 'NULL', isNull: true };
  if (typeof value === 'bigint') return { text: value.toLocaleString(), isNull: false };
  if (value instanceof Date) return { text: value.toISOString().slice(0, 10), isNull: false };
  return { text: String(value), isNull: false };
}

function columnType(id: string): string {
  return props.result?.columns.find((c) => c.name === id)?.type ?? '';
}

const pageCount = computed(() => table.getPageCount());

/* ---------------------------------------------------------------- export --- */

const menuOpen = ref(false);
const exporting = ref<string | null>(null);
const exportError = ref<string | null>(null);
const menu = ref<HTMLElement | null>(null);

const canExport = computed(() => !!props.result && props.result.rowCount > 0 && !props.running);

function onDocumentClick(event: MouseEvent) {
  if (menu.value && !menu.value.contains(event.target as Node)) menuOpen.value = false;
}
function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') menuOpen.value = false;
}
onMounted(() => {
  document.addEventListener('click', onDocumentClick);
  document.addEventListener('keydown', onKeydown);
});
onBeforeUnmount(() => {
  document.removeEventListener('click', onDocumentClick);
  document.removeEventListener('keydown', onKeydown);
});

function timestamp(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}`;
}

function download(bytes: Uint8Array, filename: string, mime: string) {
  const url = URL.createObjectURL(new Blob([bytes as BlobPart], { type: mime }));
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function runExport(format: ExportFormat) {
  menuOpen.value = false;
  exportError.value = null;
  exporting.value = format;
  try {
    const bytes = await exportQuery(props.result!.sql, format);
    download(
      bytes,
      `query-${timestamp()}.${format}`,
      format === 'csv' ? 'text/csv;charset=utf-8' : 'application/vnd.apache.parquet',
    );
  } catch (err) {
    exportError.value = err instanceof Error ? err.message : String(err);
  } finally {
    exporting.value = null;
  }
}
</script>

<template>
  <section class="panel">
    <div class="panel-head">
      <p class="label">Results</p>

      <div ref="menu" class="export">
        <button
          class="export-btn"
          type="button"
          :disabled="!canExport || !!exporting"
          :aria-expanded="menuOpen"
          @click="menuOpen = !menuOpen"
        >
          {{ exporting ? `Exporting ${exporting}…` : 'Export' }}
          <span class="caret">▾</span>
        </button>
        <ul v-if="menuOpen" class="menu">
          <li>
            <button type="button" @click="runExport('csv')">
              CSV <span>every row, comma-separated</span>
            </button>
          </li>
          <li>
            <button type="button" @click="runExport('parquet')">
              Parquet <span>every row, typed and compressed</span>
            </button>
          </li>
        </ul>
      </div>

      <p v-if="running" class="meta mono">running…</p>
      <p v-else-if="error" class="meta mono bad">query failed</p>
      <p v-else-if="result" class="meta mono">
        <b>{{ result.rowCount.toLocaleString() }}</b>
        {{ result.rowCount === 1 ? 'row' : 'rows' }}
        · {{ result.elapsedMs.toFixed(0) }} ms
        <template v-if="result.truncated">
          · showing first {{ MAX_RENDERED_ROWS.toLocaleString() }}, query not limited
        </template>
      </p>
      <p v-else class="meta mono">—</p>
    </div>

    <p v-if="exportError" class="export-error">{{ exportError }}</p>

    <!-- DuckDB's parser messages are good; an analyst debugging their own SQL
         needs the real text, not a friendly paraphrase of it. -->
    <pre v-if="error" class="error">{{ error }}</pre>

    <div v-else-if="!result" class="empty">Run a query to see results.</div>

    <div v-else-if="result.rowCount === 0" class="empty">
      That query ran fine and matched no rows.
    </div>

    <template v-else>
      <div class="scroll">
        <table>
          <thead>
            <tr>
              <th
                v-for="header in table.getHeaderGroups()[0].headers"
                :key="header.id"
                :class="{ num: isNumeric(columnType(header.column.id)) }"
                :title="`${header.column.id} — ${columnType(header.column.id)}`"
              >
                {{ header.column.id }}
              </th>
              <!-- Slack absorber. Real columns size to their contents; this takes
                   whatever is left so a two-column result still spans the panel
                   instead of huddling against the left edge. -->
              <th class="spacer" aria-hidden="true"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in table.getRowModel().rows" :key="row.id">
              <td
                v-for="cell in row.getVisibleCells()"
                :key="cell.id"
                :class="{
                  num: isNumeric(columnType(cell.column.id)),
                  null: render(cell.getValue()).isNull,
                }"
              >
                {{ render(cell.getValue()).text }}
              </td>
              <td class="spacer"></td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="pageCount > 1" class="pager">
        <button type="button" :disabled="!table.getCanPreviousPage()" @click="table.previousPage()">
          ←
        </button>
        <span class="mono">
          {{ table.getState().pagination.pageIndex + 1 }} / {{ pageCount }}
        </span>
        <button type="button" :disabled="!table.getCanNextPage()" @click="table.nextPage()">
          →
        </button>
      </div>
    </template>
  </section>
</template>

<style scoped>
.meta {
  margin: 0 0 0 auto;
  font-size: 11px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}

/* ---------------------------------------------------------------- export --- */

.export {
  order: 3;
  position: relative;
}

.export-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--mono);
  font-size: 10.5px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 600;
  padding: 5px 12px;
  border: 1px solid var(--line);
  border-radius: 3px;
  background: var(--surface);
  color: var(--ink);
}

.export-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.export-btn:disabled {
  opacity: 0.4;
  cursor: default;
}

.caret {
  font-size: 8px;
}

.menu {
  position: absolute;
  right: 0;
  top: calc(100% + 5px);
  z-index: 20;
  margin: 0;
  padding: 4px;
  list-style: none;
  min-width: 15rem;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 3px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.13);
}

.menu button {
  display: block;
  width: 100%;
  text-align: left;
  padding: 7px 9px;
  border: none;
  border-radius: 2px;
  background: none;
  font-family: var(--mono);
  font-size: 11.5px;
  font-weight: 600;
}

.menu button span {
  display: block;
  font-family: var(--sans);
  font-size: 10.5px;
  font-weight: 400;
  color: var(--muted);
  margin-top: 1px;
}

.menu button:hover {
  background: var(--accent-soft);
  color: var(--accent);
}

.export-error {
  margin: 0;
  padding: 10px 15px;
  background: var(--neg-soft);
  color: var(--neg);
  font-family: var(--mono);
  font-size: 11.5px;
  border-bottom: 1px solid var(--line);
}

/* ----------------------------------------------------------------- grid --- */

.meta b {
  color: var(--ink);
  font-weight: 600;
}

.meta.bad {
  color: var(--neg);
}

.empty {
  padding: 34px 15px;
  text-align: center;
  color: var(--muted);
  font-size: 13px;
}

.error {
  margin: 0;
  padding: 14px 15px;
  background: var(--neg-soft);
  color: var(--neg);
  font-family: var(--mono);
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

/* Capped so the grid informs the page rather than becoming it. */
.scroll {
  overflow: auto;
  max-height: 46vh;
}

/* Columns hug their contents rather than stretching to fill the panel — a
   two-column result should not spread a fund name across 900px. */
table {
  border-collapse: collapse;
  width: 100%;
  font-size: 13px;
}

/* Real columns take only what they need; .spacer takes the rest. */
th:not(.spacer),
td:not(.spacer) {
  width: 1px;
}

.spacer {
  width: auto;
  border-right: none;
  padding: 0;
}

th,
td {
  /* Vertical rules, so the eye can follow a column down a wide result. */
  border-right: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  padding: 7px 11px;
  white-space: nowrap;
  max-width: 44rem;
  overflow: hidden;
  text-overflow: ellipsis;
}

th:last-child,
td:last-child {
  border-right: none;
}

/* Column names are the reading key for the whole grid, so they carry full ink
   weight. Only the type annotation beside them recedes. */
th {
  position: sticky;
  top: 0;
  z-index: 1;
  font-family: var(--mono);
  font-size: 10.5px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ink);
  text-align: left;
  /* White, not the panel-head grey directly above it — sharing that tone merged
     the two into one grey slab and made the column names read as chrome. The
     heavier bottom rule is what separates header from data now. */
  background: var(--surface);
  font-weight: 600;
  border-bottom-color: var(--line-strong);
  border-bottom-width: 2px;
}

/* The type is on the header's title attribute rather than inline — it is
   reference, not something you read on every scan of the grid. */
th {
  cursor: help;
}

tbody tr:last-child td {
  border-bottom: none;
}

tbody tr:hover td {
  background: var(--accent-soft);
}

/* Header and body share one alignment, driven by the column's type. */
th.num,
td.num {
  text-align: right;
}

td.num {
  font-family: var(--mono);
  font-variant-numeric: tabular-nums;
}

/* Dimmed and italic, so a genuine NULL never reads as an empty cell. */
td.null {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--muted);
  font-style: italic;
}

.pager {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 15px;
  border-top: 1px solid var(--line);
  font-size: 11px;
  color: var(--muted);
}

.pager button {
  padding: 2px 9px;
  background: var(--surface-2);
  border: 1px solid var(--line);
  border-radius: 3px;
}

.pager button:disabled {
  opacity: 0.4;
  cursor: default;
}
</style>
