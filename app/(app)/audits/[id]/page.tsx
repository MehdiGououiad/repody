import dynamic from "next/dynamic";
import { notFound } from "next/navigation";
import { RunAuditReportLoader } from "@/components/audit/run-audit-report-loader";
import { fetchAudit } from "@/lib/api/server";

const RunAuditReport = dynamic(
  () =>
    import("@/components/audit/run-audit-report").then((m) => ({
      default: m.RunAuditReport,
    })),
  { loading: () => <RunAuditReportLoader /> },
);

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const audit = await fetchAudit((await params).id);
  return { title: audit ? audit.workflowName : undefined };
}

export default async function AuditDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  const audit = await fetchAudit(id);
  if (!audit) notFound();

  return <RunAuditReport audit={audit} />;
}
