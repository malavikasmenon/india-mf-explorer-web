import { resolve } from 'node:path';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  optimizeDeps: {
    // The dep prebundler rewrites duckdb-wasm's worker and .wasm asset paths,
    // which breaks instantiation with an opaque worker error. Leave it alone.
    exclude: ['@duckdb/duckdb-wasm'],
  },
  server: {
    // DuckDB-WASM reads Parquet by HTTP range request; without this the dev
    // server can serve a 200 with the whole file where a 206 was expected.
    headers: { 'Accept-Ranges': 'bytes' },
  },
  build: {
    rollupOptions: {
      // Two static pages, not one SPA with client routes: `/` is a plain HTML
      // landing page (no Vue, nothing to boot), `/app/` is the DuckDB workbench.
      input: {
        main: resolve(__dirname, 'index.html'),
        app: resolve(__dirname, 'app/index.html'),
      },
    },
  },
});
