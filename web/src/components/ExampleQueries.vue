<script setup lang="ts">
/**
 * Starter questions, taken from the manifest.
 *
 * The single biggest thing standing between someone and their first query is an
 * empty editor. These give a way in that is one click, and — because they load
 * real SQL into a visible, editable editor — they double as a tutorial for the
 * schema rather than a set of canned answers.
 *
 * The examples are published with the data, not written here, so a new table
 * arrives with its own.
 */
import type { TableExample } from '../catalog';

defineProps<{ examples: TableExample[]; active: string | null }>();
const emit = defineEmits<{ pick: [example: TableExample] }>();
</script>

<template>
  <section v-if="examples.length" class="examples">
    <p class="label">Try one</p>
    <div class="list">
      <button
        v-for="example in examples"
        :key="example.label"
        class="ex"
        type="button"
        :aria-pressed="active === example.label"
        @click="emit('pick', example)"
      >
        {{ example.label }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.examples {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.list {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.ex {
  font-size: 13px;
  text-align: left;
  padding: 7px 12px;
  border: 1px solid var(--line);
  border-radius: 3px;
  background: var(--surface);
  line-height: 1.35;
}

.ex:hover {
  border-color: var(--accent);
}

.ex[aria-pressed='true'] {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--accent);
}
</style>
