import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { Suspense } from "react";
import { Page } from "@/components/layout/page";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/ui/kbd";
import { Skeleton } from "@/components/ui/skeleton";
import { WorkflowsList } from "@/components/workflow/workflows-list";
import { $server, fetchAccess } from "@/lib/api/server";
import { getQueryClient } from "@/lib/query/get-query-client";

export async function generateMetadata() {
  return { title: (await getTranslations("nav"))("workflows") };
}

export default async function WorkflowsPage() {
  const [tNav, access] = await Promise.all([getTranslations("nav"), fetchAccess()]);
  const queryClient = getQueryClient();
  // Started, not awaited: the list streams in when the API answers.
  void queryClient.prefetchQuery($server.queryOptions("get", "/v1/workflows"));

  return (
    <Page
      title={tNav("workflows")}
      bleed
      actions={
        access.permissions.includes("workflow:write") ? (
          <Button variant="primary" render={<Link href="/workflows/new" />}>
            <Plus />
            {tNav("newWorkflow")}
            <Kbd className="ms-1">C</Kbd>
          </Button>
        ) : null
      }
    >
      <HydrationBoundary state={dehydrate(queryClient)}>
        <Suspense fallback={<Skeleton.Lines count={6} className="p-4" />}>
          <WorkflowsList />
        </Suspense>
      </HydrationBoundary>
    </Page>
  );
}
