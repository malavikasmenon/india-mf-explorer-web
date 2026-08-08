/**
 * The dataset catalog, as published by `pipeline/build_manifest.py`.
 *
 * This module is the only place that knows the manifest's shape. Nothing in the
 * app hardcodes a table name, a column name or a file path — everything is read
 * from here, which is what lets a new table appear in the UI without a code
 * change on this side.
 */
import { dataUrl } from './config';

export interface ColumnMeta {
  name: string;
  type: string;
  nullable: boolean;
  /** Part of the table's identifier. Parquet can't carry this, so the catalog does. */
  primary_key?: boolean;
  /** Absent when the column has no prose in the dictionary yet. */
  description?: string;
  source_field?: string;
}

/** A starter query, published with the table it belongs to. */
export interface TableExample {
  label: string;
  sql: string;
}

export interface TableMeta {
  name: string;
  title: string;
  /** What one row represents. Absent for tables not yet documented. */
  /** One plain sentence saying what the table is, shown under its name. */
  subtitle?: string | null;
  grain?: string | null;
  description?: string | null;
  examples?: TableExample[];
  primary_key?: string[];
  files: string[];
  row_count: number;
  bytes: number;
  source?: {
    source_url?: string | null;
    retrieved_at?: string;
    snapshot?: string;
    bytes?: number;
    last_modified?: string | null;
  } | null;
  columns: ColumnMeta[];
}

export interface Manifest {
  generated_at: string;
  tables: TableMeta[];
}

export async function fetchManifest(): Promise<Manifest> {
  const url = dataUrl('manifest.json');
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(
      `Could not load the data catalog (${response.status} from ${url}). ` +
        `If you are running locally, run \`npm run sync-data\` to copy the ` +
        `pipeline output into public/data.`,
    );
  }
  return response.json();
}

/** Shape the catalog into what @codemirror/lang-sql wants for completion. */
export function completionSchema(manifest: Manifest): Record<string, string[]> {
  return Object.fromEntries(
    manifest.tables.map((table) => [table.name, table.columns.map((c) => c.name)]),
  );
}

/**
 * Render the catalog as plain text for an LLM prompt — DuckDB's own DDL
 * dialect isn't the point here, just enough for a model to write a correct
 * query: table, grain, and each column with its type and description.
 */
export function describeSchemaForPrompt(manifest: Manifest): string {
  return manifest.tables
    .map((table) => {
      const head = `${table.name}${table.subtitle ? ` — ${table.subtitle}` : ''} (${table.row_count.toLocaleString()} rows)`;
      const cols = table.columns
        .map((c) => {
          const bits = [c.name, c.type];
          if (c.primary_key) bits.push('primary key');
          if (c.description) bits.push(`-- ${c.description}`);
          return `  ${bits.join(' ')}`;
        })
        .join('\n');
      return `${head}\n${cols}`;
    })
    .join('\n\n');
}
