import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { Suspense } from "react";
import { BusinessDashboard } from "@/components/dashboard/business-dashboard";
import { PageHeader } from "@/components/layout/page-header";
import { PageShell } from "@/components/layout/page-shell";
import { Button } from "@/components/ui/button";
import { $server } from "@/lib/api/server";
import { getQueryClient } from "@/lib/query/get-query-client";

export default async function DashboardPage() {
  const [t, tCommon] = await Promise.all([getTranslations("dashboard"), getTranslations("common")]);
  const queryClient = getQueryClient();
  // Started, not awaited: the dashboard streams in when the API answers.
  void queryClient.prefetchQuery($server.queryOptions("get", "/v1/dashboard"));

  return (
    <PageShell.Stagger>
      <PageHeader
        title={t("title")}
        description={t("pageDescription")}
        actions={
          <Button asChild size="sm" className="gap-2">
            <Link href="/workflows/new">
              <Plus className="h-4 w-4" />
              {tCommon("newWorkflow")}
            </Link>
          </Button>
        }
      />
      <HydrationBoundary state={dehydrate(queryClient)}>
        <Suspense fallback={<div className="panel-elevated rounded-xl h-[480px] animate-pulse" />}>
          <BusinessDashboard />
        </Suspense>
      </HydrationBoundary>
    </PageShell.Stagger>
  );
}
