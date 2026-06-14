import dynamic from "next/dynamic";
import { notFound } from "next/navigation";
import { RunAuditReportLoader } from "@/components/audit/run-audit-report-loader";
import { fetchAuditDetail } from "@/lib/api/client";

const RunAuditReport = dynamic(
  () =>
    import("@/components/audit/run-audit-report").then((m) => ({
      default: m.RunAuditReport,
    })),
  { loading: () => <RunAuditReportLoader /> }
);

export default async function AuditDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  const audit = await fetchAuditDetail(id);
  if (!audit) notFound();

  return <RunAuditReport audit={audit} />;
}
