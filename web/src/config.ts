/**
 * Where the published dataset lives.
 *
 * Local static files under `public/data` are a stopgap for testing the premise;
 * the real home is object storage. Every path in the app is built from this one
 * value, so moving is an env var rather than a refactor.
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
