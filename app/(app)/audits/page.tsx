import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { getTranslations } from "next-intl/server";
import type { SearchParams } from "nuqs/server";
import { Suspense } from "react";
import { AuditList } from "@/components/audit/audit-list";
import { Page } from "@/components/layout/page";
import { Skeleton } from "@/components/ui/skeleton";
import { $server } from "@/lib/api/server";
import { auditsQuery, loadAuditSearchParams } from "@/lib/audits/search-params";
import { getQueryClient } from "@/lib/query/get-query-client";

export async function generateMetadata() {
  return { title: (await getTranslations("nav"))("audits") };
}

export default async function AuditsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const [tNav, search] = await Promise.all([
    getTranslations("nav"),
    loadAuditSearchParams(searchParams),
  ]);
  const queryClient = getQueryClient();
  // Started, not awaited: the list streams in when the API answers.
  void queryClient.prefetchQuery(
    $server.queryOptions("get", "/v1/audits", { params: { query: auditsQuery(search) } })
  );
  void queryClient.prefetchQuery($server.queryOptions("get", "/v1/workflows"));

  return (
    <Page title={tNav("audits")} bleed>
      <HydrationBoundary state={dehydrate(queryClient)}>
        <Suspense fallback={<Skeleton.Lines count={10} className="p-4" />}>
          <AuditList />
        </Suspense>
      </HydrationBoundary>
    </Page>
  );
}
