/**
 * DuckDB-WASM: instantiation, view registration, and query execution.
 *
 * There is no query backend. The engine runs in a worker in the browser and
 * reads Parquet straight from object storage by HTTP range request, which is why
 * the architecture is itself the pitch — no install, no credentials, no ETL.
 */
import * as duckdb from '@duckdb/duckdb-wasm';
// Vite resolves these to emitted asset URLs; `?url` is required, a bare import
// would try to parse the .wasm as a module.
import mvpWasm from '@duckdb/duckdb-wasm/dist/duckdb-mvp.wasm?url';
import mvpWorker from '@duckdb/duckdb-wasm/dist/duckdb-browser-mvp.worker.js?url';
import ehWasm from '@duckdb/duckdb-wasm/dist/duckdb-eh.wasm?url';
import ehWorker from '@duckdb/duckdb-wasm/dist/duckdb-browser-eh.worker.js?url';

import { MAX_RENDERED_ROWS, dataUrl } from './config';
import type { Manifest } from './catalog';

/**
 * Vite's `?url` imports are root-relative in dev (`/node_modules/…/duckdb-eh.wasm`).
 * The main thread resolves those fine against the document, but the path is handed
 * to the worker, which fetches it with `new Request(url)` — and a worker has no
 * document to resolve against, so a relative URL throws "Failed to parse URL".
 * Absolutise here, where the document is still in scope.
 */
const absolute = (url: string) => new URL(url, window.location.href).href;

const BUNDLES: duckdb.DuckDBBundles = {
  mvp: { mainModule: absolute(mvpWasm), mainWorker: absolute(mvpWorker) },
  eh: { mainModule: absolute(ehWasm), mainWorker: absolute(ehWorker) },
};

export interface QueryResult {
  columns: { name: string; type: string }[];
  rows: Record<string, unknown>[];
  /** True row count of the result, which may exceed `rows.length`. */
  rowCount: number;
  truncated: boolean;
  elapsedMs: number;
  /**
   * The statement that produced these rows. Kept with the result rather than
   * read from the editor at export time — otherwise editing the query without
   * re-running it would export something other than what is on screen.
   */
  sql: string;
}

let connection: duckdb.AsyncDuckDBConnection | null = null;
let database: duckdb.AsyncDuckDB | null = null;

/**
 * Arrow names types differently from DuckDB — a result column reads back as
 * `Utf8` where the data dictionary calls it `VARCHAR`. Reconcile them, so the
 * type above a column means the same thing in the grid as it does in the rail.
 * Anything unrecognised passes through as Arrow wrote it rather than being
 * guessed at.
 */
const ARROW_TO_DUCKDB: Record<string, string> = {
  Bool: 'BOOLEAN',
  Int8: 'TINYINT',
  Int16: 'SMALLINT',
  Int32: 'INTEGER',
  Int64: 'BIGINT',
  Uint8: 'UTINYINT',
  Uint16: 'USMALLINT',
  Uint32: 'UINTEGER',
  Uint64: 'UBIGINT',
  Float32: 'FLOAT',
  Float64: 'DOUBLE',
  Utf8: 'VARCHAR',
  LargeUtf8: 'VARCHAR',
  Binary: 'BLOB',
  Null: 'NULL',
};

function typeName(arrowType: unknown): string {
  const raw = String(arrowType);
  if (raw in ARROW_TO_DUCKDB) return ARROW_TO_DUCKDB[raw];
  // Parameterised types stringify with their parameters: Date32<DAY>,
  // Timestamp<MICROSECOND>, Decimal<38,5>. Keep the head, drop the noise.
  const head = raw.split('<')[0];
  if (head.startsWith('Date')) return 'DATE';
  if (head.startsWith('Timestamp')) return 'TIMESTAMP';
  if (head.startsWith('Time')) return 'TIME';
  if (head.startsWith('Decimal')) return 'DECIMAL';
  return head.toUpperCase();
}

/**
 * DuckDB pulls its Parquet extension from `extensions.duckdb.org` on first use,
 * so booting is not actually offline-capable. When that host is unreachable the
 * failure surfaces as "function signature mismatch"; when it is merely slow,
 * nothing settles at all and the page sits on the loading screen forever.
 *
 * Neither is diagnosable, so bound the wait and say what actually went wrong.
 */
const BOOT_TIMEOUT_MS = 45_000;
const EXTENSION_HOST = 'https://extensions.duckdb.org';

function bootTimeout(): Promise<never> {
  return new Promise((_, reject) =>
    setTimeout(
      () =>
        reject(
          new Error(
            `The query engine did not start within ${BOOT_TIMEOUT_MS / 1000}s.\n\n` +
              `DuckDB loads its Parquet extension from ${EXTENSION_HOST} at startup, ` +
              `so this usually means that host is unreachable or slow — check your ` +
              `network, VPN, or proxy. Everything else here is served locally.`,
          ),
        ),
      BOOT_TIMEOUT_MS,
    ),
  );
}

/**
 * Boot the engine and expose one view per table in the manifest.
 *
 * The views are what make this feel like a database rather than a file reader:
 * an analyst writes `FROM schemes` and never sees a URL, and adding a table upstream
 * is enough to make it queryable here.
 */
export async function initDuckDB(manifest: Manifest): Promise<void> {
  await Promise.race([connect(manifest), bootTimeout()]);
}

async function connect(manifest: Manifest): Promise<void> {
  const bundle = await duckdb.selectBundle(BUNDLES);
  const worker = new Worker(bundle.mainWorker!);
  const db = new duckdb.AsyncDuckDB(new duckdb.ConsoleLogger(duckdb.LogLevel.WARNING), worker);
  await db.instantiate(bundle.mainModule, bundle.pthreadWorker);

  database = db;
  connection = await db.connect();

  for (const table of manifest.tables) {
    // Always a list literal, so a single file and a set of monthly partitions
    // take the identical code path here and in the pipeline.
    const files = table.files.map((f) => `'${dataUrl(f)}'`).join(', ');
    try {
      // hive_partitioning=false: the year=/month= folders are a storage
      // layout, not columns - left on, DuckDB auto-detects them and adds
      // redundant year/month columns that duplicate what `date` carries.
      await connection.query(
        `CREATE OR REPLACE VIEW "${table.name}" AS SELECT * FROM read_parquet([${files}], hive_partitioning = false)`,
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      // The Parquet reader is what fails when the extension never arrived, and
      // DuckDB's own wording for it gives no clue where to look.
      if (/signature mismatch|not been installed|Extension/i.test(message)) {
        throw new Error(
          `Could not load DuckDB's Parquet extension from ${EXTENSION_HOST}.\n\n` +
            `The dataset itself is served locally, but DuckDB-WASM fetches this ` +
            `extension over the network at startup. Check your connection, then ` +
            `hard-reload.\n\nOriginal error: ${message}`,
        );
      }
      throw new Error(`Could not register table "${table.name}": ${message}`);
    }
  }
}

export async function runQuery(sql: string): Promise<QueryResult> {
  if (!connection) throw new Error('The query engine is still starting up.');

  const started = performance.now();
  const result = await connection.query(sql);
  const elapsedMs = performance.now() - started;

  const columns = result.schema.fields.map((field) => ({
    name: field.name,
    type: typeName(field.type),
  }));

  const rowCount = result.numRows;
  const limit = Math.min(rowCount, MAX_RENDERED_ROWS);
  const rows: Record<string, unknown>[] = [];

  for (let i = 0; i < limit; i++) {
    const source = result.get(i);
    const row: Record<string, unknown> = {};
    for (const { name } of columns) row[name] = source?.[name] ?? null;
    rows.push(row);
  }

  return { columns, rows, rowCount, truncated: rowCount > limit, elapsedMs, sql };
}

export type ExportFormat = 'csv' | 'parquet';

const COPY_OPTIONS: Record<ExportFormat, string> = {
  csv: '(FORMAT csv, HEADER)',
  parquet: '(FORMAT parquet, COMPRESSION zstd)',
};

/**
 * Write the query's results to a file inside DuckDB's virtual filesystem and
 * hand back the bytes.
 *
 * The statement is re-run rather than serialising what the grid holds: the grid
 * is capped at MAX_RENDERED_ROWS, and an export that silently stopped at 1,000
 * of 14,222 rows would be worse than no export at all. DuckDB also writes real
 * Parquet and properly quoted CSV, which is not worth reimplementing in JS.
 */
export async function exportQuery(sql: string, format: ExportFormat): Promise<Uint8Array> {
  if (!connection || !database) throw new Error('The query engine is still starting up.');

  // COPY (SELECT …;) is a syntax error, and trailing semicolons are habitual.
  const statement = sql.trim().replace(/;\s*$/, '');
  if (!statement) throw new Error('There is no query to export.');

  const name = `export-${Date.now()}.${format}`;
  try {
    await connection.query(`COPY (${statement}) TO '${name}' ${COPY_OPTIONS[format]}`);
    return await database.copyFileToBuffer(name);
  } finally {
    // Best effort: leaving files in the virtual FS would leak memory across
    // repeated exports, but a failed cleanup must not mask the real error.
    try {
      await database.dropFile(name);
    } catch {
      /* ignore */
    }
  }
}
