# Open Indian Fund Data — Design Brief

> Handoff document. Written 2026-08-02 after a long scoping session.
> Read this before writing code — it records what's been verified, what's been
> ruled out, and what's still open, so none of it gets re-derived.

---

## 1. What this is

A free, open platform to query Indian mutual fund data like a database, with
natural-language search as an on-ramp rather than the main interface.

**The product is the join, not the data.** All the underlying data is already
public. What doesn't exist anywhere is a version that's already parsed, joined
on consistent keys, documented, and queryable without first writing a scraper
and standing up a database. Everyone who analyses this data today repeats the
same four hours of ETL in private.

Analogy: BigQuery public datasets, or a notebook with the data already loaded.

### Metric that matters

**Time to first query.** Zero setup, zero signup, zero ETL. The demo is: open
page, type question, get answer.

### Positioning guardrail

A **screener** answers pre-set questions. A **warehouse** answers arbitrary ones.
Resist filter dropdowns in the UI — every dropdown is a question you've decided
for the user. Keep raw SQL a first-class path; the users who'd star the repo
want the editor, not the chatbot.

Keep the framing **descriptive** ("what funds hold, and where that came from"),
never prescriptive ("what to buy"). Investment advice is a regulated activity
in India.

---

## 2. Context

Built for the BestPossible.AI hackathon.

| Date | What |
|---|---|
| Aug 1–10, 2026 | Solo build window |
| **Aug 10, 2026** | Submit deployed app + screencast |
| Aug 13, 2026 | Selections / invitations |
| Aug 23–26, 2026 | Dharamshala finale — Aug 24–25 are heads-down building with mentors, Aug 26 is demo day |

**Aug 10 is an audition, not the finish line.** The real judging is Aug 26. So
ship the smallest thing that is unambiguously deployed and working, and hold the
ambitious parts back for the on-site build days.

Hackathon requirements: deployed app, usable UI, mobile responsive, user auth,
backend with persistence, public open-source repo with commit history, and
meaningful AI integration.

Note: the organisers' own idea generator lists "Build with AI" (using AI tools to
build) as a valid answer alongside "Build with an AI feature." Both count, but
judging is cumulative — having both scores better than having one.

---

## 3. Ruled out (don't re-litigate)

| Idea | Why it died |
|---|---|
| Dataset uptime monitor via YAML config | **Gatus** (Apache-2.0) already does exactly this — YAML-configured health dashboard. Uptime Kuma also open source. |
| Repo-scanning auto-discovery monitor | Still a monitor underneath; most discovered sources need credentials; weak impact story. |
| BESCOM power-cut tracker | BESCOM publishes only *planned* outage circulars. Unscheduled outages — the interesting ones — aren't collected at all. Would collapse into crowdsourcing, which needs behaviour change at scale. |
| Govt PDF → accessible HTML | Bottleneck is government adoption, not technology. |
| Holdings archive as the headline | Too narrow a pitch. Holdings stay valuable as *depth* (see phase 3) but don't lead with them. |
| Returns-only screener | NAV is already solved by mfapi/mftool. Competing with Value Research on data everyone has. |

---

## 4. Phase 1 schema — two tables, raw only

> **Naming, settled 2026-08-03.** The dimension table is **`schemes`**, not `mf`
> or `mutual_funds`. Plural, per the prevailing SQL/warehouse convention that a
> table is named for the set it holds. Not "funds", because the grain is one row
> per *scheme code* — a single fund routinely has four or more, being the
> Direct/Regular × Growth/IDCW variants. Naming it for funds would bake a wrong
> grain into the name and collide with the fund-level grouping `portfolio_key`
> introduces in phase 2 (§10). AMFI and SEBI both say "scheme".

Every column is published by AMFI verbatim. Nothing parsed out of name strings,
nothing computed.

The `row field N` comments below are positions in **`NAVAll.txt`**. The history
export orders its columns differently (§5.5) — don't reuse the numbers.

⚠️ **These constraints do not survive to Parquet.** Parquet has no primary keys
and no foreign keys; the browser gets flat columns. So this DDL is a contract the
*pipeline* asserts before publishing — load into DuckDB with the constraints on,
verify no `nav` row references a missing `scheme_code`, then export. Treat a
violation as a failed build, not a warning.

```sql
-- one row per AMFI scheme code
CREATE TABLE schemes (
  scheme_code             INTEGER PRIMARY KEY,  -- row field 1
  isin_div_payout_growth  VARCHAR,              -- row field 2
  isin_div_reinvestment   VARCHAR,              -- row field 3
  scheme_name             VARCHAR NOT NULL,     -- row field 4, verbatim
  fund_house              VARCHAR NOT NULL,     -- AMC header line
  scheme_type             VARCHAR NOT NULL,     -- header, before '('
  scheme_category         VARCHAR NOT NULL      -- header, inside '(...)'
);

-- one row per scheme per day
-- Sourced from the history export, so field numbers differ from schemes above:
--                                    NAVAll.txt | history export
CREATE TABLE nav (
  scheme_code INTEGER NOT NULL REFERENCES schemes(scheme_code),  -- field 1 | field 1
  nav_date    DATE    NOT NULL,               -- DD-Mon-YYYY, field 6 | field 8
  nav         DECIMAL(18,5),                  --              field 5 | field 5
  PRIMARY KEY (scheme_code, nav_date)
);
```

### Four judgment calls (decided)

1. **`-` becomes `NULL`.** The dash is a text-file convention for absence, not a
   value. Only deviation from strict verbatim. In the history export the same
   absence is an **empty string** — map that to `NULL` too.
2. **`scheme_code` is INTEGER.** Its type in both AMFI and mfapi; the join key
   on every query.
3. **Bad NAVs store as `NULL`, row retained.** Dropping the row destroys the
   evidence that AMFI published something broken that day.

   This applies only to values that *mean* absence. Junk that is genuinely junk
   stays verbatim. Observed in the 2026-08-02 snapshot, both in
   `isin_div_reinvestment`: **`Redeemed`** (9 rows) and **`HDFCNIVODG`** (1 row).
   `NOTAPP` was cited in an earlier draft but does not appear in this snapshot —
   don't code against a fixed list of junk values, just don't normalise them away.
4. **Upsert on `(scheme_code, nav_date)`.** Makes re-ingestion free, weekend runs
   harmless, and any day re-runnable. **Never infer a file-level date.**

---

## 5. Verified source facts

All of the following was checked against live sources on 2026-08-02, not assumed.

### 5.1 The AMFI file

`https://portal.amfiindia.com/spages/NAVAll.txt`
(`www.amfiindia.com` 302-redirects to `portal.` — use the portal host directly)

Semicolon-delimited and **hierarchical**. Section headers carry the dimensional
data, so no separate scheme master is needed.

```
Scheme Code;ISIN Div Payout/ISIN Growth;ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date

Open Ended Schemes(Hybrid Scheme - Dynamic Asset Allocation or Balanced Advantage)
└─ scheme_type ─────┘ └─ scheme_category ──────────────────────────────────────┘

HDFC Mutual Fund
└─ fund_house ─┘

118968;INF179K01WA6;-;HDFC Balanced Advantage Fund - Growth Plan - Direct Plan;572.34500;31-Jul-2026
```

**Column names matter:** field 2 is `ISIN Div Payout/ISIN Growth` (one field),
field 3 is `ISIN Div Reinvestment`. Not "payout" and "growth" as two fields.

Pedantic but real: the literal header in `NAVAll.txt` is `ISIN Div Payout/ ISIN
Growth`, with a space after the slash. The history export writes the same column
without it. Don't match on the header string.

**Measured 2026-08-02** — 1,644,555 bytes, 14,222 data rows, every one exactly 6
fields, 2,262 blank lines, 1,175 header lines. All 14,222 scheme codes are
distinct, so `scheme_code` is a genuine primary key.

### 5.2 Parse rules — four line types, two state variables

Corrected 2026-08-02 against the full file. The earlier version of this table
was wrong in three places; all three are marked below.

| Line | Test | Action |
|---|---|---|
| blank | empty **after `strip()`** — separators are a single space, not empty | skip |
| `Scheme Code;ISIN Div…` | starts with "Scheme Code" | skip — appears **once**, at the top, not repeated |
| `Open Ended Schemes(…)` | no `;` · matches `^(.+?)\((.+)\)$` · **group 1 ends with "Schemes"** | **set** scheme_type + scheme_category |
| `HDFC Mutual Fund` | no `;` · anything else | **set** fund_house |
| `118968;INF179…` | has `;` | **emit** row with current state |

⚠️ **The parenthesis alone does not identify a section header.** `IL&FS Mutual
Fund (IDF)` is a fund house with parentheses in its name. Testing on `(` reads it
as a scheme type, which leaves `fund_house` stuck on the *previous* AMC for all
12 of its schemes — silently, with no error raised. This is the one landmine in
the file.

The reliable discriminator: all three scheme-type values end in `Schemes` —
`Open Ended Schemes`, `Close Ended Schemes`, `Interval Fund Schemes` — and no
fund house does. Semicolon still separates headers from data.

Fail loudly on anything unexpected (wrong field count, data row before any
header, non-integer scheme code). A silent mis-parse here corrupts the dimension
table for every downstream join.

### 5.3 Dates are per-row, not per-file

The file is **"latest known NAV per scheme code,"** not "today's NAV for
everything." Most rows carry the current date; some carry dates going back years
(observed as far back as `20-Aug-2015`). Stale rows are discontinued share
classes, bonus options, and **segregated portfolios** — side-pocketed assets from
debt-fund credit events, whose NAV freezes permanently.

Free consequence: comparing each scheme's `max(nav_date)` to the file's dominant
date gives you `is_active` and answers "which funds quietly stopped reporting"
with no extra source.

⚠️ A WebFetch of this file **truncates** — it returned only the debt section.
Any proportion estimates from that sample are unreliable. Parse the full file
locally to get real numbers.

### 5.4 Publishing schedule

Per SEBI (`sebi.gov.in/sebi_data/commondocs/cirimd05_h.html`):

- **11:00 PM IST** each business day for regular schemes
- **10:00 AM next business day** for Fund of Funds
- Delays past 9 PM must be explained in writing to AMFI

**Run the cron at ~11:00 AM IST.** Both deadlines for the previous business day
have passed, so one pass gets a fully settled day. A midnight run
systematically misses every fund-of-funds.

### 5.5 Historical NAV — ❌ the AMFI bulk export does not work

**Retracted 2026-08-03.** The earlier entry here recorded
`https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx?frmdt=…&todt=…`
as verified live returning `text/plain`, 60,657,474 bytes in 42s, and the whole
`nav` plan was built on it. **That result does not reproduce, and the endpoint
appears never to have worked this way.** What it actually returns:

- Every GET — with `frmdt`/`todt`, with `tp=1`, with `mf=`, with a session
  cookie, with none — returns the page's own **HTML form**, `text/html`,
  13,694 bytes, in ~15s. Never data.
- The page is an ASP.NET WebForms postback: `__VIEWSTATE` + `__EVENTVALIDATION`
  + `ctl00$amfiHomeContent$btnViewReport`. Query parameters are not read.
- It is also **broken server-side** and not merely awkward: the "Select Mutual
  Fund" `<select>` renders with **zero `<option>` elements**, and there is only
  one date input (`txtFrmDate`) — no to-date, so it is not a range export at
  all. Its own JS enforces `ValidateOneMonthPeriod`.
- A bare GET 302s to `https://www.amfiindia.com/nav-history-download`, which
  **404s**.

Do not spend time on this again without first checking whether the AMC dropdown
has options. Everything downstream of it is blocked until it does.

⚠️ The most likely explanation is that the original "verification" was a
WebFetch that returned a plausible-looking summary rather than a real HTTP
result — note that §5.3 carries the same warning about WebFetch truncating this
host. **Treat any source fact in this document that was not produced by a
locally-run request as unverified.**

**Consequence:** the backfill uses mfapi (§5.6) instead. AMFI's `NAVAll.txt`
remains the source for `schemes` and for the daily `nav` append, so ongoing data
is still first-party; only history is mirrored.

### 5.6 mfapi is NAVAll.txt parsed — nothing more

`https://api.mfapi.in/mf/118968/latest` returns:

```json
{ "meta": {
    "fund_house": "HDFC Mutual Fund",
    "scheme_type": "Open Ended Schemes",
    "scheme_category": "Hybrid Scheme - Dynamic Asset Allocation or Balanced Advantage",
    "scheme_code": 118968,
    "scheme_name": "HDFC Balanced Advantage Fund - Growth Plan - Direct Plan",
    "isin_growth": "INF179K01WA6",
    "isin_div_reinvestment": null } }
```

Every field maps to the AMFI file. It adds exactly two conveniences: `-` → `null`,
and per-scheme JSON access. It renames field 2 to `isin_growth`, which is lossy —
that column serves both payout and growth variants. **Keep AMFI's naming.**

Endpoints: `/mf/search?q=`, `/mf?limit=&offset=`, `/mf/{code}?startDate=&endDate=`,
`/mf/{code}/latest`. No auth, states no rate limiting.

**Promoted to the backfill source 2026-08-03**, since §5.5 has no working
alternative. `/mf/{code}` returns that scheme's full history since inception.
Measured over 40 randomly sampled schemes at concurrency 8: **18.6 req/s, 40/40
succeeded, ~65 KB and ~1,660 NAV points each** → ~13 minutes and ~0.93 GB for
all 14,222 schemes. One call per scheme is unavoidable; there is no bulk
endpoint.

⚠️ **The licensing problem in §6 is now load-bearing, not theoretical.** mfapi
states no license and will not name its source, and it is now upstream of every
historical row this project republishes. Two ways out, neither taken yet:
migrate the backfill to `captn3m0/historical-mf-data` (**MIT**, redistributable,
but no type/category — those would still come from AMFI's headers), or publish
`nav` history only as a derived artefact with the provenance stated. Until one
is chosen, the `nav` backfill is fine to query locally and **not clearly safe to
republish**. `schemes` and the daily append are unaffected — they are AMFI-direct.

### 5.7 AMC naming conventions diverge — this is why phase 2 is separate

Two real rows, same concept, incompatible conventions:

```
Aditya Birla Sun Life Banking & PSU Debt Fund - DIRECT - IDCW
HDFC Balanced Advantage Fund - Growth Plan - Direct Plan
```

Different position (before vs after the option), different casing, different
wording. Forty-odd AMCs, no shared convention, and no field that states it.

---

## 6. Licensing — unresolved, and it matters

| Source | License | Position |
|---|---|---|
| `captn3m0/historical-mf-data` | **MIT** | Permits redistribution and derivative works. **But** per direct inspection it lacks fund type / category — those only exist in AMFI's section headers. So using it means joining MIT NAV history to an AMFI-sourced dimension table. |
| `mfapi.in` | **none stated** | Free and unlimited, but no license and won't name its source. Awkward upstream for a provenance-first project. |
| **AMFI direct** | **restrictive** | See below. |

AMFI Terms of Use (`amfiindia.com/terms-of-use`), verbatim:

> "…for your **personal and non-commercial use only**"
> "You may not… publicly display, transmit, **publish**… anything available through the Site"
> "You may not… modify, or **create derivative works** based on anything available through the Site"
> "You shall **not store electronically any significant portion** of any part of the Site."

**Counterweight** (not legal advice): NAV values are facts, and facts aren't
copyrightable — India rejected sweat-of-the-brow in *Eastern Book Company v.
D.B. Modak* (2008). India has no sui generis database right. AMFI's leverage is
contract, not copyright. The data exists because SEBI mandates disclosure for
investor transparency. Multiple projects (captn3m0, mfapi, mftool) have operated
publicly for years.

**Working resolution:**

> **The licensing question is a *publishing* question, not a *development*
> question.** Pulling a sample to build against is personal use. The terms bite
> when you republish the archive. Do not let this block writing code.

Before publishing: lead the product on the derived layer (your own computation,
original work) rather than a raw mirror; and email AMFI for written approval —
their clause says "without our written approval," which implies approval exists.

---

## 7. Architecture

Total cost at this scale: effectively zero.

| Piece | Choice | Why |
|---|---|---|
| Query engine | **DuckDB-WASM in browser** | No query backend at all. The architecture *is* the pitch — no install, no credentials, no ETL. |
| Data files | **Parquet on Cloudflare R2** | Zero egress fees. S3 charges bandwidth. |
| Published dataset | **Hugging Face Datasets** | Free, git-versioned, viewer, citable. |
| Frontend | **React + Vite on Cloudflare Pages** | Static SPA. (Use Vue if better known — 8 days is no time to learn a framework.) |
| SQL editor | CodeMirror 6 + `@codemirror/lang-sql` | Feed autocomplete from the data dictionary. |
| Results grid | TanStack Table | |
| Auth + app state | **Supabase free tier** | Postgres + auth bundled. Auth is a hackathon requirement; don't build it. |
| Ingestion | **GitHub Actions cron** | Free on public repos, and runs are publicly visible — good credibility for a data project. |
| LLM calls | **One serverless function** | The only server-side code. Keeps the API key off the client. |
| Pipeline | **Python + DuckDB** | `python-calamine` for xlsx, `httpx` for fetching. Transforms in SQL. |

**Use DuckDB in the pipeline too.** One SQL dialect across pipeline, browser, and
the NL→SQL prompt. Any query is testable locally against the exact files the
browser loads.

### Non-negotiables

- **Partition Parquet by month from day one** (`nav/2026-05.parquet`). Scaling
  from 3 months to 5 years becomes "write more files," not a rewrite.
- **Stable URLs.** Once someone points a notebook at a path, it's a contract.
  Decide the scheme now; changing it later silently breaks every downstream user.
  A `manifest.json` listing the published partitions is probably part of that
  contract, not an implementation detail — the browser likely can't glob over
  plain HTTPS and must be told which files exist (§12.5). It's also the natural
  home for row counts and a "data through" date for the provenance panel.
- **Sort each `nav` partition by `scheme_code`.** Row-group statistics then let a
  single-fund query skip most of the file. Helps per-scheme lookups a lot,
  category-wide scans not at all — those need Parquet bloom filters, which is a
  later optimisation, not a day-one one.
- **Two LICENSE files** — code (MIT/Apache-2.0) and data (CC-BY-4.0) — stated
  plainly in the README.

---

## 8. Build approach

**Sample first, then scale.**

1. Pull **3 months** of data. `schemes` = **14,222 rows** (measured, not estimated);
   `nav` ≈ 900,000 rows; ~5–15 MB as Parquet. Ideal dev size — performance
   problems are real, reloads are instant, fits DuckDB-WASM with no pagination
   tricks.
2. Build the site against real data. UI decisions that mocks can't answer:
   14,222 fund names in a picker, 90-character scheme names, actual Parquet load
   time, what an empty result set looks like.
3. Backfill afterwards. Same code, more loop iterations.

### Build state — 2026-08-02

**Done: `schemes`.** `pipeline/amfi.py` fetches and parses `NAVAll.txt`;
`pipeline/build_schemes.py` loads it into DuckDB with the §4 constraints on, validates,
and writes `data/schemes.parquet` (14,222 rows, 253 KB zstd, sorted by `scheme_code`).

Verified after the build, not assumed: all 12 `IL&FS Mutual Fund (IDF)` rows carry
the correct fund house; zero `fund_house` values contain "Schemes"; NULL count is
exactly 10,503, matching the dash count in source, with no dashes leaking through;
a spot-checked row matches the raw bytes including a double space inside the name.

Provenance goes to a `data/schemes.ingest.json` sidecar rather than into `schemes` columns,
which keeps §4's "every column verbatim" true. **Open:** the README promises
provenance *per row* — if that's meant literally, `schemes` needs `source_file` and
`retrieved_at` columns and §4's principle needs rewording.

The `mutualfund` PyPI package was evaluated and skipped — three commits on main is
thin for the core data path, and it wraps away the section-header hierarchy, which
is precisely the part that carries the dimensional data.

### Build state — 2026-08-03

**Done: the manifest.** `pipeline/build_manifest.py` writes `data/manifest.json`,
the published index of the dataset. Types, row counts and file lists are measured
from the Parquet at build time; the prose (grain, column descriptions, source
field) lives in `pipeline/dictionary.py`. A table or column with no prose still
publishes with its types, so documentation is an enrichment and never a gate.

This is the `manifest.json` §7 anticipated, and it settles **§12.5** — its `files`
array is the explicit partition enumeration that stands in for the glob a public
bucket can't support. `nav` will list its monthly partitions there and need no new
logic on either side.

**Done: the web workbench.** `web/` — Vue 3 + Vite + DuckDB-WASM. Data dictionary
rail, CodeMirror SQL editor with completions fed from the manifest, TanStack
results grid. It contains no table name, column name or file path: it fetches the
manifest and registers `CREATE VIEW` per table, so `FROM schemes` works and a new table
appears with zero frontend changes. Verified by adding a throwaway second table
and confirming it listed, queried and joined without a code edit.

Verified in Chrome against the counts above, not assumed: 14,222 / 52 / 86, the 12
`IL&FS Mutual Fund (IDF)` rows, and 9,702 NULL `isin_div_reinvestment` rendering
as visible NULLs rather than blanks. Queries run in 7–21 ms with zero console
errors. Full-table `SELECT *` reports the true 14,222 while rendering 1,000 — the
user's SQL is never rewritten.

⚠️ **Node ≥ 20.19 is required** (Vite 7+). `web/.nvmrc` pins 26.

**Correction:** an earlier version of this line claimed "the 90-day history file
is fetched and sitting on disk." It never was — `data/raw/` held only the
`NAVAll.txt` snapshot. See §5.5 for what the history endpoint actually does.

---

## 9. UI — already designed

Wireframe: <https://claude.ai/code/artifact/09337cf0-0db5-4411-b022-342ae9d19453>
Schema doc: <https://claude.ai/code/artifact/fdeea0f7-244c-4d3f-a42b-bf7ac4ade6f2>

Decisions the wireframe encodes:

- **Data dictionary is a permanent left rail**, not a docs page — visible while
  querying. Each table shows its *grain*.
- **Generated SQL is always visible and editable**, even in Ask mode, labelled
  "this runs, not the question." NL drafts, the user verifies. Converts the model
  from an oracle into a drafting assistant.
- **Provenance is its own panel**, not a tooltip.
- **A "use it from your own tool" panel** — a `duckdb.sql()` snippet against
  hosted Parquet, plus bulk download. Proves the ETL is genuinely gone, and makes
  it a public data resource that happens to have a web app rather than a web app
  with data in it.

Palette is ledger-ish: muted green-grey neutrals, ochre accent, semantic
green/rust reserved for deltas. Mono carries labels, data and SQL.

---

## 10. Phase 2 and 3 (post-Aug-10, for the Dharamshala build days)

**Phase 2 — derived layer.** Parse `plan_type` / `option_type` out of
`scheme_name`, derive `portfolio_key` (strip plan/option tokens so the four
variants of one fund collapse together), and precompute `fund_stats`.

The messy tail of name normalization is a genuine job for the model — the clean
80% is string rules.

`portfolio_key` unlocks **the flagship query**: Direct vs Regular. Same portfolio,
same manager, only the fee differs, so NAV divergence measures the distributor
commission exactly. Most people don't know they're paying it, and every "free"
tool that upsells them is conflicted about showing it. Report it in **rupees on
₹1L over 5 years**, not just a percentage.

**Phase 3 — holdings.** Monthly portfolio disclosures (XLSX per AMC), keyed on
`portfolio_key` because holdings are disclosed once per portfolio, not per plan.
No clean API exists — this is the part nobody archives, and every month not
collected is gone permanently. Unlocks: new positions, fund overlap,
concentration screening.

### Query catalogue (★ = rarely done well by free tools)

- ★★ Direct vs Regular: what the distributor commission actually cost
- ★ Rolling return distributions, not one endpoint-sensitive trailing number
- ★ Quartile persistence — did the fund stay good, or have one lucky year
- ★ Category dispersion — is the best large-cap fund meaningfully better than
  the worst, or should you just buy the index
- ★ Funds that quietly stopped reporting NAV
- Top/bottom performers per sub-category; max drawdown and recovery time;
  volatility ranked within category; SIP XIRR; side-by-side comparison

---

## 11. Domain traps that will corrupt the data

1. **Direct vs Regular breaks every ranking.** Same portfolio, lower expense
   ratio, higher NAV. Rank without holding plan type constant and Direct sweeps
   the top for reasons unrelated to the manager. Default to
   `plan_type = 'Direct'`, `option_type = 'Growth'`.
2. **TRI vs PRI.** SEBI requires benchmarking against the **Total Return Index**
   (includes dividends). Freely available index data is often **Price Return
   Index** (excludes them) — worth ~1%/yr. Benchmark against PRI and every fund
   looks like it beat the market.
3. **Trailing CAGR is endpoint-sensitive.** Move the start date a month and the
   ranking reshuffles. Compute **rolling returns** too.
4. **Category is not static.** "Large cap" = top 100 by market cap, and AMFI
   republishes that list semi-annually. SEBI issued a **new categorization
   circular on 2026-02-26** tightening rules for focused, contra, dividend-yield
   and value funds. Storing category as a flat column loses history.
5. **Debt portfolios have different columns** — YTM, Macaulay duration, credit
   ratings, and instruments like TREPS/repo that have no ISIN.

### Reading

- [Zerodha Varsity — Personal Finance](https://zerodha.com/varsity/modules/):
  [intro to MF](https://zerodha.com/varsity/chapter/introduction-to-mutual-funds/),
  [NAV](https://zerodha.com/varsity/chapter/concept-of-fund-nav/),
  [**the fact sheet**](https://zerodha.com/varsity/chapter/the-mutual-fund-fact-sheet/) (read twice — it's the Rosetta Stone between the file and the meaning),
  [expense ratio / direct vs regular](https://zerodha.com/varsity/chapter/mutual-fund-expense-ratio-direct-and-regular-plans/)
- [SEBI Master Circular for Mutual Funds](https://www.sebi.gov.in/sebi_data/attachdocs/1337083696184.pdf) — skim for disclosure obligations
- [SEBI FAQs for MF Investors](https://www.sebi.gov.in/sebi_data/faqfiles/sep-2024/1727242783639.pdf) — same content, readable
- [PwC on scheme categorisation](https://www.pwc.in/assets/pdfs/financial-service/categorisation-of-mutual-fund-schemes.pdf)

---

## 12. Open questions

### Resolved 2026-08-02

- ~~**Does the history endpoint return section headers?**~~ **Yes.** One request
  gives both tables. See §5.5.
- ~~**What's the real row count for `schemes`?**~~ **14,222** schemes, 52 fund houses,
  3 scheme types, 86 categories, zero duplicate scheme codes. See §5.1.

### Still open

1. **What proportion of rows are stale?** The other half of the old question 4 —
   needs `nav` parsed before `is_active` means anything (§5.3).
2. **Which source do you publish from?** MIT dataset + AMFI dimensions, or AMFI
   direct with written approval.
3. **Send the AMFI email?** Costs one email; a "yes" removes the whole question.
4. **Benchmark index data licensing** — NSE/BSE terms are murky. Affects any
   "beat the benchmark" feature.
5. ~~**Does `read_parquet` glob over plain HTTPS?**~~ **Sidestepped, not answered.**
   `data/manifest.json` enumerates each table's files explicitly, so the browser
   never needs to glob. See §8. Whether globbing would have worked is now moot.
6. **Vendor DuckDB's Parquet extension?** Discovered 2026-08-03 while debugging a
   stuck loading screen: DuckDB-WASM fetches
   `https://extensions.duckdb.org/v1.5.4/wasm_eh/parquet.duckdb_extension.wasm`
   **at startup**, every session. So "queries run on your machine, nothing is
   sent to a server" is not quite true, and the app cannot boot offline or behind
   a proxy that blocks that host. Verified by blocking it: DuckDB reports only
   `function signature mismatch`, and when the host is slow rather than blocked
   nothing settles at all.

   `web/src/duckdb.ts` now bounds the wait and explains the failure, but that
   makes it *diagnosable*, not *fixed*. The real fix is serving the extension
   ourselves via `custom_extension_repository`, which means vendoring a file
   whose path is pinned to DuckDB's version (`v1.5.4/wasm_eh/…`) and re-vendoring
   on every `@duckdb/duckdb-wasm` bump. Worth doing before the demo — a CDN blip
   during judging kills the whole app.
7. **Are R2's CORS and `Range` headers configured correctly?** DuckDB-WASM reads
   the Parquet footer then fetches row groups by byte range. If the bucket doesn't
   expose `Content-Length` / `Content-Range` / `Accept-Ranges` cross-origin, it
   either silently downloads whole files or fails — and the error won't mention
   CORS. This is the most common way this architecture breaks. Verify early.
8. **Provenance per row, or per ingest?** See §8. Affects whether §4's
   "every column verbatim" survives as stated.
