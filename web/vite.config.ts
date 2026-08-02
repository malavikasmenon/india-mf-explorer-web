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
});
