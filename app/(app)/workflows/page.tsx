import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { Suspense } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { PageShell } from "@/components/layout/page-shell";
import { Button } from "@/components/ui/button";
import { WorkflowsList } from "@/components/workflow/workflows-list";
import { $server } from "@/lib/api/server";
import { getQueryClient } from "@/lib/query/get-query-client";

export default async function WorkflowsPage() {
  const [t, tNav] = await Promise.all([getTranslations("workflows"), getTranslations("nav")]);
  const queryClient = getQueryClient();
  // Started, not awaited: the list streams in when the API answers.
  void queryClient.prefetchQuery($server.queryOptions("get", "/v1/workflows"));

  return (
    <PageShell>
      <PageHeader
        title={t("title")}
        description={t("description")}
        eyebrow={t("eyebrow")}
        actions={
          <Button asChild>
            <Link href="/workflows/new">
              <Plus className="h-4 w-4" />
              {tNav("newWorkflow")}
            </Link>
          </Button>
        }
      />
      <HydrationBoundary state={dehydrate(queryClient)}>
        <Suspense
          fallback={
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 h-48 animate-pulse" />
          }
        >
          <WorkflowsList />
        </Suspense>
      </HydrationBoundary>
    </PageShell>
  );
}
