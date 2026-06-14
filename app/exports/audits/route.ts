import { fetchAudits } from "@/lib/api/client";

function csvCell(value: string | number | null | undefined): string {
  const text = value == null ? "" : String(value);
  return `"${text.replaceAll('"', '""')}"`;
}

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
  const csv = rows.map((row) => row.map(csvCell).join(",")).join("\r\n");
  const filename = `audit-runs-${new Date().toISOString().slice(0, 10)}.csv`;

  return new Response(`\uFEFF${csv}`, {
    headers: {
      "content-type": "text/csv; charset=utf-8",
      "content-disposition": `attachment; filename="${filename}"`,
      "cache-control": "no-store",
    },
  });
}
