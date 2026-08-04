<script setup lang="ts">
/**
 * The marketing page. Deliberately does not boot DuckDB-WASM — that's a
 * multi-MB engine load, and paying that cost here just to show a "try it"
 * demo made the first paint feel broken. The manifest fetch (a small JSON
 * file) is enough to source the example questions; clicking one hands the
 * SQL off to the real editor at /app/ instead of running it in place.
 */
import { onMounted, ref } from 'vue';
import ThemeToggle from './components/ThemeToggle.vue';
import { fetchManifest, type TableExample } from './catalog';

const examples = ref<TableExample[]>([]);

// Snapshot figures, not a live query — see the script comment above for why.
// Update by hand if these drift noticeably from data_pipeline/manifest.py's output.
const stats = {
  schemes: 14234,
  fundHouses: 52,
  historyYears: 20,
};

onMounted(async () => {
  try {
    const loaded = await fetchManifest();
    examples.value = loaded.tables.flatMap((t) => t.examples ?? []);
  } catch {
    // The demo chips are a nice-to-have on this page; a manifest hiccup here
    // shouldn't block the rest of the page from rendering.
  }
});

function openInEditor(example: TableExample) {
  window.location.href = `/app/?q=${encodeURIComponent(example.sql)}`;
}
</script>

<template>
  <header class="l-nav">
    <a class="wordmark mono" href="/">OPEN <span>INDIAN</span> FUND DATA</a>
    <div class="l-nav-right">
      <a class="l-explore" href="/app/">Explorer</a>
      <ThemeToggle />
    </div>
  </header>

  <main>
    <section class="l-hero">
      <div class="l-hero-copy">
        <p class="label l-eyebrow">Free · open data · no signup</p>
        <h1>Indian mutual fund data,<br />queryable like a database.</h1>
        <p class="l-sub">
          The scheme dimension and daily NAV history, sourced from AMFI and joined
          for you. Ask one of these and open it straight in the editor, or go
          write your own.
        </p>
        <a class="l-explore l-explore-big" href="/app/">Explore the data →</a>
      </div>

      <div class="panel l-demo">
        <div class="panel-head l-demo-head">
          <p class="label">Try a question</p>
        </div>

        <div class="l-chips">
          <button
            v-for="ex in examples"
            :key="ex.label"
            type="button"
            class="l-chip mono"
            @click="openInEditor(ex)"
          >
            {{ ex.label }}
          </button>
        </div>

        <p class="l-demo-hint mono">Opens the query in the editor at /app/, ready to run.</p>
      </div>
    </section>

    <section class="l-section l-split">
      <div>
        <p class="label">What this is</p>
        <p>
          AMFI publishes mutual fund data publicly, but as a hierarchical text file
          built for nobody to actually read. The good research tools charge for
          access; the free ones want your phone number first.
        </p>
        <p>
          This platform takes that raw public data, parses and joins it, and puts a
          real query engine on top. Write SQL yourself, or click one of the
          questions above — either way you're looking at the same underlying data.
        </p>
      </div>
      <div>
        <p class="label">What it's not</p>
        <ul class="l-not-list">
          <li>Not investment advice</li>
          <li>Not a broker or distributor</li>
          <li>Not behind a paywall</li>
          <li>Not collecting your data to sell</li>
          <li>Not recommending any fund</li>
          <li>Not affiliated with AMFI or any AMC</li>
        </ul>
      </div>
    </section>

    <section class="l-section">
      <p class="label">Data coverage</p>
      <div class="l-stats">
        <div class="l-stat">
          <span class="l-stat-n mono">{{ stats.schemes.toLocaleString() }}</span>
          <span class="l-stat-k">Schemes</span>
        </div>
        <div class="l-stat">
          <span class="l-stat-n mono">{{ stats.fundHouses }}</span>
          <span class="l-stat-k">Fund houses</span>
        </div>
        <div class="l-stat">
          <span class="l-stat-n mono">{{ stats.historyYears }}+ yrs</span>
          <span class="l-stat-k">NAV history depth</span>
        </div>
      </div>
    </section>
  </main>

  <footer class="footer l-footer">
    <div class="foot-col">
      <p class="label">Source</p>
      <p>
        Published daily by <a href="https://www.amfiindia.com/" target="_blank" rel="noopener">AMFI</a>
        under SEBI's disclosure mandate. Every column is stored exactly as published.
      </p>
    </div>
    <div class="foot-col">
      <p class="label">Not financial advice</p>
      <p>
        A data tool. It describes what funds are and what they have returned, and
        shows where every number came from. It does not recommend investments.
      </p>
    </div>
  </footer>
</template>

<style scoped>
.l-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 40px;
  border-bottom: 1px solid var(--line);
  background: var(--surface);
}

.wordmark {
  color: var(--ink);
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.wordmark span {
  color: var(--accent);
}

.l-nav-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.l-explore {
  font-family: var(--mono);
  font-size: 12.5px;
  font-weight: 600;
  color: var(--accent);
  text-decoration: none;
  white-space: nowrap;
}

main {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 40px;
}

.l-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 460px);
  align-items: center;
  gap: 56px;
  padding: 76px 0 88px;
}

.l-eyebrow {
  margin: 0 0 16px;
}

.l-hero h1 {
  margin: 0 0 18px;
  font-size: clamp(32px, 3.4vw, 46px);
  font-weight: 800;
  line-height: 1.12;
  letter-spacing: -0.01em;
}

.l-sub {
  max-width: 480px;
  color: var(--muted);
  font-size: 15.5px;
  line-height: 1.6;
}

.l-hero-copy .l-explore-big {
  margin-top: 28px;
}

.l-demo {
  text-align: left;
}

.l-demo-head {
  justify-content: flex-start;
}

.l-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  padding: 14px 15px 0;
}

.l-chip {
  font-size: 12px;
  text-align: left;
  padding: 7px 11px;
  border: 1px solid var(--line);
  border-radius: 3px;
  background: var(--surface);
  color: var(--muted);
  line-height: 1.35;
}

.l-chip:hover {
  border-color: var(--accent);
  color: var(--ink);
}

.l-demo-hint {
  margin: 12px 15px 15px;
  font-size: 11px;
  color: var(--muted);
}

.l-section {
  padding: 46px 0;
  border-top: 1px solid var(--line);
}

.l-section > p {
  color: var(--muted);
  font-size: 15px;
  line-height: 1.65;
  max-width: 640px;
}

.l-split {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 36px;
}

.l-split p {
  color: var(--muted);
  font-size: 14px;
  line-height: 1.6;
  margin: 8px 0 0;
}

.l-not-list {
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.l-not-list li {
  padding-left: 16px;
  position: relative;
  font-size: 14px;
  color: var(--muted);
}

.l-not-list li::before {
  content: '—';
  position: absolute;
  left: 0;
  color: var(--line-strong);
}

.l-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-top: 10px;
}

.l-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.l-stat-n {
  font-size: 26px;
  font-weight: 700;
}

.l-stat-k {
  font-size: 12px;
  color: var(--muted);
}

.l-explore-big {
  display: inline-block;
  padding: 11px 20px;
  border-radius: var(--radius);
  background: var(--accent);
  color: var(--on-accent);
  font-weight: 600;
}

.l-explore-big:hover {
  opacity: 0.9;
}

/* .footer/.foot-col aren't shared from App.vue — Vue's <style scoped> is
   per-component, so these have to be restated here rather than assumed. */
.footer {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 26px;
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

.l-footer {
  max-width: 1180px;
  margin: 0 auto;
  padding: 26px 40px;
  border-left: none;
  border-right: none;
}

@media (max-width: 900px) {
  .l-hero {
    grid-template-columns: minmax(0, 1fr);
    gap: 40px;
    padding: 56px 0 64px;
  }
}

@media (max-width: 640px) {
  main {
    padding: 0 16px;
  }

  .l-nav {
    padding: 14px 16px;
  }

  .l-footer {
    padding: 26px 16px;
  }

  .l-split,
  .l-stats {
    grid-template-columns: 1fr;
  }
}
</style>
