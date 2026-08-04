<script setup lang="ts">
/**
 * The data dictionary, as a permanent rail — visible while querying rather than
 * parked on a docs page.
 *
 * Deliberately terse. Each table shows its name, size, grain, and a two-column
 * list of fields; the prose for a column is a tooltip, not a paragraph, because
 * seven paragraphs of it stacked up read as a wall rather than a reference.
 *
 * Rendered entirely from the manifest — no table or column is named in this file.
 */
import type { TableMeta } from '../catalog';

defineProps<{ tables: TableMeta[] }>();
const emit = defineEmits<{ insert: [text: string] }>();

function compact(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}
</script>

<template>
  <aside class="rail">
    <p class="label">Data dictionary</p>

    <div class="dict">
      <section v-for="table in tables" :key="table.name" class="tbl">
        <header class="tbl-head">
          <button class="tbl-name mono" type="button" @click="emit('insert', table.name)">
            {{ table.name }}
          </button>
          <span class="tbl-rows mono">{{ compact(table.row_count) }}</span>
        </header>

        <!-- One sentence saying what the table is. A bare name plus a column list
             leaves someone new to guess at the subject matter. -->
        <p v-if="table.subtitle" class="subtitle">{{ table.subtitle }}</p>

        <!-- A grid rather than a table: the name column needs to truncate under
             pressure, and only `minmax(0, 1fr)` makes that reliable while still
             aligning the type and key markers down the card. -->
        <div class="cols">
          <template v-for="column in table.columns" :key="column.name">
            <button
              type="button"
              class="c-name mono"
              :title="
                column.description ? `${column.name} — ${column.description}` : column.name
              "
              @click="emit('insert', column.name)"
            >
              {{ column.name }}
            </button>
            <span class="c-type mono">{{ column.type }}</span>
          </template>
        </div>
      </section>
    </div>

    <p class="note">
      Click any name to drop it into the editor. Hover a field for what it means.
    </p>
  </aside>
</template>

<style scoped>
.rail {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 22px 20px 40px;
}

.dict {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tbl {
  border: 1px solid var(--line);
  border-radius: 3px;
  background: var(--surface);
  padding: 9px 11px 6px;
}

.tbl-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
}

.tbl-name {
  padding: 0;
  border: none;
  background: none;
  font-family: var(--mono);
  font-size: 12.5px;
  font-weight: 600;
}

.tbl-name:hover {
  color: var(--accent);
}

.tbl-rows {
  font-size: 10px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}

.subtitle {
  margin: 4px 0 9px;
  font-size: 11.5px;
  line-height: 1.4;
  color: var(--muted);
}

.cols {
  display: grid;
  /* The name absorbs slack and truncates; type takes only what it needs, so
     nothing can be pushed out through the card's right edge however long a
     field name gets. */
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: baseline;
  column-gap: 12px;
  row-gap: 7px;
}

.c-name {
  padding: 0;
  border: none;
  background: none;
  font-size: 11px;
  text-align: left;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.c-name:hover {
  color: var(--accent);
  text-decoration: underline;
}

.c-type {
  font-size: 9.5px;
  color: var(--muted);
  text-align: right;
  white-space: nowrap;
}

.note {
  margin: 2px 0 0;
  font-size: 11.5px;
  line-height: 1.45;
  color: var(--muted);
  border-left: 2px solid var(--accent);
  padding-left: 10px;
}

@media (max-width: 900px) {
  .rail {
    border-bottom: 1px solid var(--line);
    padding-bottom: 22px;
  }
}
</style>
