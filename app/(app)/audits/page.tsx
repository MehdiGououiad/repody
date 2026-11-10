import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { getTranslations } from "next-intl/server";
import type { SearchParams } from "nuqs/server";
import { Suspense } from "react";
import { AuditList } from "@/components/audit/audit-list";
import { PageHeader } from "@/components/layout/page-header";
import { PageShell } from "@/components/layout/page-shell";
import { $server } from "@/lib/api/server";
import { auditsQuery, loadAuditSearchParams } from "@/lib/audits/search-params";
import { getQueryClient } from "@/lib/query/get-query-client";

export default async function AuditsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const [t, search] = await Promise.all([
    getTranslations("audits"),
    loadAuditSearchParams(searchParams),
  ]);
  const queryClient = getQueryClient();
  // Started, not awaited: the list streams in when the API answers.
  void queryClient.prefetchQuery(
    $server.queryOptions("get", "/v1/audits", { params: { query: auditsQuery(search) } })
  );
  void queryClient.prefetchQuery($server.queryOptions("get", "/v1/workflows"));

  return (
    <PageShell>
      <PageHeader title={t("title")} description={t("description")} eyebrow={t("eyebrow")} />
      <HydrationBoundary state={dehydrate(queryClient)}>
        <Suspense fallback={<div className="panel-elevated rounded-xl h-96 animate-pulse" />}>
          <AuditList />
        </Suspense>
      </HydrationBoundary>
    </PageShell>
  );
}
