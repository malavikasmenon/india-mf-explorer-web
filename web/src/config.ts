/**
 * Where the published dataset lives.
 *
 * Locally this defaults to `/data`, served from `public/data` — populated by
 * `npm run sync-data` (part of `npm run dev` / `npm run build`) copying the
 * pipeline's own local output. That copy step only makes sense with a local
 * `data/` folder to copy from, though, so it's not part of a production
 * build: `npm run build:prod` skips it and relies entirely on this env var
 * instead, set at Netlify build time to the data repo's jsDelivr URL
 * (https://cdn.jsdelivr.net/gh/<user>/open-mf-data-india@main/data) — the
 * production app fetches straight from there at runtime, never from
 * whatever built it. Every path in the app is built from this one value, so
 * moving the dataset elsewhere is an env var change, not a refactor.
 */
export const DATA_BASE_URL = import.meta.env.VITE_DATA_BASE_URL ?? '/data';

/** Absolute URL for a path in the dataset. DuckDB needs absolute, not relative. */
export function dataUrl(path: string): string {
  return new URL(`${DATA_BASE_URL}/${path}`, window.location.origin).toString();
}

/**
 * Rows materialised into the grid. The query itself is never rewritten — an
 * analyst's SQL runs exactly as typed — but rendering 14k DOM rows helps nobody,
 * so the cap is applied after the fact and always shown alongside the true count.
 */
export const MAX_RENDERED_ROWS = 1000;
