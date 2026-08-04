/**
 * Site-wide light/dark theme, shared by the landing page and the app.
 *
 * `prefers-color-scheme` picks the default; a manual choice is remembered in
 * localStorage and wins over it from then on, via a `data-theme` attribute
 * that styles.css keys off. The attribute is also set synchronously by an
 * inline script in each page's <head> (see index.html / app/index.html) so
 * there is no flash of the wrong theme before this module loads.
 */
const KEY = 'oifd-theme';

export type Theme = 'light' | 'dark';

export function getTheme(): Theme {
  const stored = localStorage.getItem(KEY);
  if (stored === 'light' || stored === 'dark') return stored;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function setTheme(theme: Theme): void {
  localStorage.setItem(KEY, theme);
  document.documentElement.dataset.theme = theme;
}

export function toggleTheme(): Theme {
  const next: Theme = getTheme() === 'dark' ? 'light' : 'dark';
  setTheme(next);
  return next;
}
