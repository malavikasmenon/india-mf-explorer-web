/**
 * DuckDB-WASM's Arrow bindings don't box DATE/TIMESTAMP columns into JS Date
 * objects — they arrive as raw epoch-millisecond numbers (or a bigint of
 * epoch micros for TIMESTAMP), so the column's declared type decides how a
 * plain number gets read rather than the value's own JS type. Shared by
 * ResultsGrid and the landing page's live demo so both format cells the
 * same way.
 */
export function renderCell(value: unknown, type: string): { text: string; isNull: boolean } {
  if (value === null || value === undefined) return { text: 'NULL', isNull: true };
  if (type === 'DATE' && typeof value === 'number') {
    return { text: new Date(value).toISOString().slice(0, 10), isNull: false };
  }
  if (type === 'TIMESTAMP' && (typeof value === 'number' || typeof value === 'bigint')) {
    return { text: new Date(Number(value)).toISOString().replace('T', ' ').slice(0, 19), isNull: false };
  }
  if (typeof value === 'bigint') return { text: value.toLocaleString(), isNull: false };
  if (value instanceof Date) return { text: value.toISOString().slice(0, 10), isNull: false };
  return { text: String(value), isNull: false };
}
