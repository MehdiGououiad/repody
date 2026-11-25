/** What a second read of a document saw differently from the first (ExtractionMeta.unconfirmed),
 * said briefly enough for one line under the field: a table or list names the rows, columns or
 * items that differ instead of repeating the whole second read. */

/** One difference, worded by the report (audits.report.diff*). */
export type ReadDifference =
  | { kind: "value"; value: unknown } // a single value: the second read's
  | { kind: "cell"; row: number; column: string; value: unknown } // a table cell (row from 1)
  | { kind: "item"; item: number; value: unknown } // a list item (from 1)
  | { kind: "rows"; first: number; second: number } // the tables have different lengths
  | { kind: "items"; first: number; second: number }; // the lists have different lengths

/** At most this many differences are named; the rest are counted. */
export const MAX_DIFFERENCES = 3;

/** As the backend compares two reads (repody.extraction.fields): text without case or extra
 * spaces, numbers by value. */
function comparable(value: unknown): unknown {
  if (typeof value === "string") return value.split(/\s+/).filter(Boolean).join(" ").toLowerCase();
  if (typeof value === "number") return Math.round(value * 1e6) / 1e6;
  if (Array.isArray(value)) return value.map(comparable);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, comparable(v)]));
  }
  return value ?? null;
}

const same = (a: unknown, b: unknown) =>
  JSON.stringify(comparable(a)) === JSON.stringify(comparable(b));

const isRow = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

/** The differences between the first read's value and the second's, in reading order. */
export function readDifferences(first: unknown, second: unknown): ReadDifference[] {
  if (!Array.isArray(first) || !Array.isArray(second)) return [{ kind: "value", value: second }];
  const table = [...first, ...second].some(isRow);
  if (first.length !== second.length) {
    return [{ kind: table ? "rows" : "items", first: first.length, second: second.length }];
  }
  const differences: ReadDifference[] = [];
  second.forEach((row, index) => {
    const before = first[index];
    if (same(before, row)) return;
    if (table && isRow(row) && isRow(before)) {
      for (const column of new Set([...Object.keys(before), ...Object.keys(row)])) {
        if (!same(before[column], row[column])) {
          differences.push({ kind: "cell", row: index + 1, column, value: row[column] ?? null });
        }
      }
    } else {
      differences.push({ kind: "item", item: index + 1, value: row });
    }
  });
  return differences;
}
