import Papa from "papaparse";
import { fetchAudits } from "@/lib/api/client";

export async function GET() {
  const { audits } = await fetchAudits();
  const rows = [
    ["id", "status", "workflow", "entity", "timestamp", "rows", "failedRules"],
    ...audits.map((audit) => [
      audit.id,
      audit.status,
      audit.workflowName,
      audit.entity,
      audit.timestamp,
      audit.rows,
      audit.failedRules,
    ]),
  ];
  // escapeFormulae: cells starting with = + - @ cannot run as spreadsheet formulas.
  const csv = Papa.unparse(rows, { quotes: true, escapeFormulae: true });
  const filename = `audit-runs-${new Date().toISOString().slice(0, 10)}.csv`;

  return new Response(`\uFEFF${csv}`, {
    headers: {
      "content-type": "text/csv; charset=utf-8",
      "content-disposition": `attachment; filename="${filename}"`,
      "cache-control": "no-store",
    },
  });
}
