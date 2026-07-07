import { Suspense } from "react";
import { getTranslations } from "next-intl/server";
import { PageHeader } from "@/components/layout/page-header";
import { PageShell } from "@/components/layout/page-shell";
import { AuditList } from "@/components/audit/audit-list";
import { AuditListExport } from "@/components/audit/audit-list-export";
import { fetchAudits } from "@/lib/api/client";

export default async function AuditsPage() {
  const [t, tCommon, auditRes] = await Promise.all([
    getTranslations("audits"),
    getTranslations("common"),
    fetchAudits().catch(() => ({
      audits: [] as Awaited<ReturnType<typeof fetchAudits>>["audits"],
      total: 0,
      limit: 200,
      offset: 0,
    })),
  ]);

  const audits = auditRes.audits;

  return (
    <PageShell>
      <PageHeader
        title={t("title")}
        description={t("description")}
        eyebrow="Reports"
        actions={
          <AuditListExport audits={audits} label={tCommon("exportCsv")} />
        }
      />
      <Suspense fallback={<div className="panel-elevated rounded-xl h-48 animate-pulse" />}>
        <AuditList audits={audits} />
      </Suspense>
    </PageShell>
  );
}
