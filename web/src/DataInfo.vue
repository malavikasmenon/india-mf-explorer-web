<script setup lang="ts">
/**
 * The /dictionary/ page: what tables exist, how they join, and where each
 * one comes from. A reference page, not the workbench — it does not boot
 * DuckDB, same reasoning as Landing.vue. Fully static: columns, types, join
 * keys, cardinality and source prose are all hand-written here, because an
 * ER diagram is describing the *shape* of the dataset, which doesn't change
 * release to release the way row counts do.
 */
import ThemeToggle from './components/ThemeToggle.vue';
import TableCard, { type CardColumn } from './components/TableCard.vue';

const schemesCols: CardColumn[] = [
  { name: 'scheme_code', type: 'varchar', pk: true },
  { name: 'scheme_name', type: 'varchar' },
  { name: 'fund_house', type: 'varchar' },
  { name: 'scheme_type', type: 'varchar' },
  { name: 'scheme_category', type: 'varchar' },
  { name: 'isin_div_payout_growth', type: 'varchar' },
  { name: 'isin_div_reinvestment', type: 'varchar' },
];

const navCols: CardColumn[] = [
  { name: 'scheme_code', type: 'varchar', pk: true, fk: true },
  { name: 'date', type: 'date', pk: true },
  { name: 'nav', type: 'double' },
];

const aumCols: CardColumn[] = [
  { name: 'scheme_code', type: 'varchar', pk: true, fk: true },
  { name: 'period', type: 'varchar', pk: true },
  { name: 'aum_excl_fof_domestic_incl_fof_overseas', type: 'double' },
  { name: 'aum_fof_domestic', type: 'double' },
];

const terCols: CardColumn[] = [
  { name: 'nsdl_scheme_code', type: 'varchar', pk: true },
  { name: 'ter_date', type: 'date', pk: true },
  { name: 'scheme_name', type: 'varchar' },
  { name: 'scheme_type', type: 'varchar' },
  { name: 'scheme_category', type: 'varchar' },
  { name: 'regular_ber', type: 'double' },
  { name: 'regular_brokerage_cost', type: 'double' },
  { name: 'regular_transaction_cost', type: 'double' },
  { name: 'regular_statutory_levies', type: 'double' },
  { name: 'regular_ter', type: 'double' },
  { name: 'direct_ber', type: 'double' },
  { name: 'direct_brokerage_cost', type: 'double' },
  { name: 'direct_transaction_cost', type: 'double' },
  { name: 'direct_statutory_levies', type: 'double' },
  { name: 'direct_ter', type: 'double' },
];

interface SourceRow {
  table: string;
  source: string;
  url: string;
  cadence: string;
}

const sources: SourceRow[] = [
  {
    table: 'schemes',
    source: 'AMFI — NAVAll.txt',
    url: 'https://www.amfiindia.com/spages/NAVAll.txt',
    cadence: 'Daily',
  },
  {
    table: 'nav',
    source: 'mfapi.in — /mf/latest (one-time /mf/{scheme_code} backfill)',
    url: 'https://api.mfapi.in',
    cadence: 'Daily',
  },
  {
    table: 'aum',
    source: 'AMFI — Average AUM, scheme-wise',
    url: 'https://www.amfiindia.com/aum-data/average-aum',
    cadence: 'Weekly (source itself publishes quarterly)',
  },
  {
    table: 'ter',
    source: 'AMFI — TER disclosure',
    url: 'https://www.amfiindia.com/ter-of-mf-schemes',
    cadence: 'Daily',
  },
];
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
    <section class="d-intro">
      <p class="label">Data</p>
      <h1>What's in the dataset</h1>
      <p class="d-sub">
        Four tables, sourced from AMFI and mfapi.in and refreshed on their own
        schedules. Three join on <code class="mono">scheme_code</code>; one doesn't.
      </p>
    </section>

    <section class="d-section">
      <p class="label">How the tables join</p>

      <div class="panel erd-panel">
        <div class="erd">
          <div class="hub-col">
            <TableCard
              title="schemes"
              subtitle="One row per AMFI scheme code."
              :columns="schemesCols"
            />
            <div class="stem-wrap">
              <div class="stem" />
              <span class="mult mono" title="One scheme_code in schemes">1</span>
            </div>
          </div>

          <div class="children">
            <div class="child">
              <div class="stem-wrap">
                <div class="stem" />
                <span class="mult mono" title="Many rows in nav per scheme_code">N</span>
              </div>
              <TableCard
                title="nav"
                subtitle="One row per scheme per day."
                :columns="navCols"
              />
            </div>
            <div class="child">
              <div class="stem-wrap">
                <div class="stem" />
                <span class="mult mono" title="Many rows in aum per scheme_code">N</span>
              </div>
              <TableCard
                title="aum"
                subtitle="One row per scheme per quarter."
                :columns="aumCols"
              />
            </div>
          </div>

          <div class="standalone-col">
            <TableCard
              title="ter"
              subtitle="One row per scheme per day."
              :columns="terCols"
              standalone
            />
          </div>
        </div>

        <p class="erd-note">
          One <code class="mono">schemes</code> row matches many rows in
          <code class="mono">nav</code> and <code class="mono">aum</code> (1:N), joined on
          <code class="mono">scheme_code</code>. <code class="mono">ter</code> stands alone —
          AMFI discloses it against NSDL's own scheme code, a different registry with no
          column in common with the rest of this dataset.
        </p>
      </div>
    </section>

    <section class="d-section">
      <p class="label">Source &amp; refresh cadence</p>

      <div class="panel">
        <table class="d-sources">
          <thead>
            <tr>
              <th></th>
              <th>Table</th>
              <th>Source of data</th>
              <th>Refresh cadence</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in sources" :key="row.table">
              <td class="mono d-n">{{ i + 1 }}</td>
              <td class="mono d-table">{{ row.table }}</td>
              <td>
                <a :href="row.url" target="_blank" rel="noopener">{{ row.source }}</a>
              </td>
              <td class="d-cadence">{{ row.cadence }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </main>

  <footer class="footer l-footer">
    <div class="foot-col">
      <p class="label">Source</p>
      <p>
        Published daily by
        <a href="https://www.amfiindia.com/" target="_blank" rel="noopener">AMFI</a>
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
  flex: 1;
}

.d-intro {
  padding: 52px 0 8px;
  max-width: 640px;
}

.d-intro h1 {
  margin: 10px 0 10px;
  font-size: clamp(26px, 2.8vw, 34px);
  font-weight: 800;
  letter-spacing: -0.01em;
}

.d-sub {
  margin: 0;
  color: var(--muted);
  font-size: 14.5px;
  line-height: 1.6;
}

.d-sub code {
  font-size: 13px;
  color: var(--ink);
}

.d-section {
  padding: 36px 0;
  border-top: 1px solid var(--line);
}

.d-section > .label {
  margin-bottom: 14px;
}

.erd-panel {
  padding: 28px 20px 22px;
}

.erd {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.hub-col {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stem-wrap {
  position: relative;
  display: flex;
  justify-content: center;
}

.stem {
  width: 1px;
  height: 24px;
  background: var(--line-strong);
}

/* The cardinality mark sits beside its line rather than breaking it — a
   gap in the connector would read as two lines, not one labelled one. */
.mult {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(7px, -50%);
  font-size: 9.5px;
  font-weight: 700;
  color: var(--muted);
  white-space: nowrap;
}

.children {
  display: flex;
  justify-content: center;
  gap: 48px;
  width: fit-content;
  border-top: 1px solid var(--line-strong);
}

.child {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.standalone-col {
  margin-top: 30px;
  padding-top: 14px;
  border-top: 1px dashed var(--line);
  width: 100%;
  display: flex;
  justify-content: center;
}

.erd-note {
  margin: 24px auto 0;
  max-width: 620px;
  text-align: center;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--muted);
}

.erd-note code {
  color: var(--ink);
  font-size: 11.5px;
}

.d-sources {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.d-sources th {
  text-align: left;
  font-family: var(--mono);
  font-size: 10.5px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 500;
  padding: 10px 15px;
  background: var(--surface-2);
  border-bottom: 1px solid var(--line);
}

.d-sources td {
  padding: 11px 15px;
  border-bottom: 1px solid var(--line);
  vertical-align: baseline;
}

.d-sources tr:last-child td {
  border-bottom: none;
}

.d-n {
  color: var(--muted);
  width: 1%;
}

.d-table {
  font-weight: 600;
  white-space: nowrap;
}

.d-sources a {
  color: var(--accent);
}

.d-cadence {
  color: var(--muted);
  white-space: nowrap;
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
  .children {
    gap: 28px;
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

  .d-sources {
    display: block;
    overflow-x: auto;
  }

  /* The tree stops fitting a phone width well before it stops fitting a
     tablet; below this it collapses to a plain stacked list with the tags
     on each card carrying the join relationship instead of the lines. */
  .erd {
    align-items: stretch;
  }

  .hub-col,
  .children,
  .child {
    align-items: stretch;
  }

  .children {
    flex-direction: column;
    gap: 14px;
    border-top: none;
    width: 100%;
  }

  .stem-wrap {
    display: none;
  }
}
</style>
