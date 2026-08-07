<script setup lang="ts">
/**
 * One table's box in the ER diagram on the /dictionary/ page. `standalone`
 * marks `ter`, which shares no join key with the others — dashed border
 * rather than the solid one the joined tables get, so the diagram reads
 * the relationship without needing a caption.
 */
export interface CardColumn {
  name: string;
  /** As DuckDB reports it, e.g. "varchar", "double". */
  type: string;
  /** Part of the table's primary key. */
  pk?: boolean;
  /** Joins to schemes.scheme_code. */
  fk?: boolean;
}

defineProps<{
  title: string;
  subtitle?: string;
  columns: CardColumn[];
  standalone?: boolean;
}>();
</script>

<template>
  <div class="card panel" :class="{ standalone }">
    <div class="card-head">
      <span class="card-title mono">{{ title }}</span>
    </div>
    <p v-if="subtitle" class="card-sub">{{ subtitle }}</p>
    <div class="card-cols">
      <!-- Name grows and wraps; type takes only what it needs on the right,
           the same split SchemaRail uses — nothing here can push past the
           card's own edge however long a name or type string gets. -->
      <template v-for="c in columns" :key="c.name">
        <span class="c-name mono">
          {{ c.name }}
          <span v-if="c.pk" class="tag tag-pk" title="Primary key">PK</span>
          <span v-if="c.fk" class="tag tag-fk" title="Joins to schemes.scheme_code">JOIN</span>
        </span>
        <span class="c-type mono">{{ c.type }}</span>
      </template>
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

.card-title {
  font-size: 13px;
  font-weight: 700;
}

.card-sub {
  margin: 4px 0 9px;
  font-size: 11px;
  line-height: 1.4;
  color: var(--muted);
}

.card-cols {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  column-gap: 10px;
  row-gap: 6px;
}

.c-name {
  font-size: 11px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px 6px;
  overflow-wrap: anywhere;
  min-width: 0;
}

.c-type {
  font-size: 9.5px;
  color: var(--muted);
  white-space: nowrap;
  align-self: start;
  padding-top: 1px;
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
