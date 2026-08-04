<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { getTheme, toggleTheme, type Theme } from '../theme';

const theme = ref<Theme>('light');

onMounted(() => {
  theme.value = getTheme();
});

function flip() {
  theme.value = toggleTheme();
}
</script>

<template>
  <button
    class="theme-toggle mono"
    type="button"
    :aria-label="theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'"
    :title="theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'"
    @click="flip"
  >
    {{ theme === 'dark' ? '☀' : '☾' }}
  </button>
</template>

<style scoped>
.theme-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: var(--surface);
  color: var(--ink);
  font-size: 20px;
  line-height: 1;
}

.theme-toggle:hover {
  border-color: var(--accent);
  color: var(--accent);
}
</style>
