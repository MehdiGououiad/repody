import {
  createLoader,
  type inferParserType,
  parseAsInteger,
  parseAsIsoDate,
  parseAsString,
  parseAsStringLiteral,
} from "nuqs/server";

export const PAGE_SIZE = 25;
export const OUTCOMES = ["passed", "warning", "failed"] as const;

/** The audits page's filters and page, as URL search params (shared by server and client). */
export const auditSearchParams = {
  q: parseAsString.withDefault(""),
  outcome: parseAsStringLiteral(OUTCOMES),
  workflow: parseAsString,
  day: parseAsIsoDate,
  page: parseAsInteger.withDefault(1),
};

export const loadAuditSearchParams = createLoader(auditSearchParams);

export type AuditSearch = inferParserType<typeof auditSearchParams>;

/** The `GET /v1/audits` query for a search: the same object on server and client, so the
 * prefetched page and the browser's query share one cache entry. */
export function auditsQuery({ q, outcome, workflow, day, page }: AuditSearch) {
  return {
    q: q || undefined,
    outcome: outcome ?? undefined,
    workflowId: workflow ?? undefined,
    day: day ? day.toISOString().slice(0, 10) : undefined,
    limit: PAGE_SIZE,
    offset: (Math.max(1, page) - 1) * PAGE_SIZE,
  };
}

/** The same filters for `GET /v1/audits/export.csv` (every matching audit, no paging). */
export function auditsExportHref(search: AuditSearch): string {
  const { limit: _limit, offset: _offset, ...filters } = auditsQuery(search);
  const params = new URLSearchParams(
    Object.entries(filters).filter((entry): entry is [string, string] => entry[1] !== undefined)
  );
  return `/api/v1/audits/export.csv${params.size ? `?${params}` : ""}`;
}
