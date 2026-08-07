<script setup lang="ts">
/**
 * One table's box in the ER diagram on the /data/ page. `standalone` marks
 * `ter`, which shares no join key with the others — dashed border rather
 * than the solid one the joined tables get, so the diagram reads the
 * relationship without needing a caption.
 */
export interface CardColumn {
  name: string;
  /** Part of the table's primary key. */
  pk?: boolean;
  /** Joins to schemes.scheme_code. */
  fk?: boolean;
}

defineProps<{
  title: string;
  subtitle?: string;
  rowCount?: number | null;
  columns: CardColumn[];
  standalone?: boolean;
}>();

function compact(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}
</script>

<template>
  <div class="card panel" :class="{ standalone }">
    <div class="card-head">
      <span class="card-title mono">{{ title }}</span>
      <span v-if="rowCount != null" class="card-rows mono">{{ compact(rowCount) }} rows</span>
    </div>
    <p v-if="subtitle" class="card-sub">{{ subtitle }}</p>
    <div class="card-cols">
      <span v-for="c in columns" :key="c.name" class="c-name mono">
        {{ c.name }}
        <span v-if="c.pk" class="tag tag-pk" title="Primary key">PK</span>
        <span v-if="c.fk" class="tag tag-fk" title="Joins to schemes.scheme_code">JOIN</span>
      </span>
    </div>
  </div>
</template>

<style scoped>
.card {
  width: 100%;
  max-width: 258px;
  padding: 11px 13px 12px;
  text-align: left;
}

.standalone {
  border-style: dashed;
  background: var(--surface-2);
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
}

.card-title {
  font-size: 13px;
  font-weight: 700;
}

.card-rows {
  font-size: 10px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.card-sub {
  margin: 4px 0 9px;
  font-size: 11px;
  line-height: 1.4;
  color: var(--muted);
}

.card-cols {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.c-name {
  font-size: 11px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px 6px;
  overflow-wrap: anywhere;
}

.tag {
  font-family: var(--mono);
  font-size: 8.5px;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 1px 4px;
  border-radius: 2px;
  line-height: 1.5;
}

.tag-pk {
  color: var(--accent);
  background: var(--accent-soft);
}

.tag-fk {
  color: var(--pos);
  background: var(--pos-soft);
}
</style>
