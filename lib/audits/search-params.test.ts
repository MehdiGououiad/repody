import { describe, expect, it } from "bun:test";
import { auditsExportHref, auditsQuery, PAGE_SIZE } from "@/lib/audits/search-params";

const search = { q: "", outcome: null, workflow: null, day: null, page: 1 };

describe("audit search params", () => {
  it("become the API query, page by page", () => {
    expect(auditsQuery({ ...search, page: 3 })).toEqual({
      q: undefined,
      outcome: undefined,
      workflowId: undefined,
      day: undefined,
      limit: PAGE_SIZE,
      offset: 2 * PAGE_SIZE,
    });
    const day = new Date("2026-11-02T00:00:00Z");
    expect(auditsQuery({ ...search, outcome: "failed", day }).day).toBe("2026-11-02");
  });

  it("export every matching audit (filters, no paging)", () => {
    expect(auditsExportHref(search)).toBe("/api/v1/audits/export.csv");
    expect(auditsExportHref({ ...search, workflow: "wf-1", page: 4 })).toBe(
      "/api/v1/audits/export.csv?workflowId=wf-1"
    );
  });
});
