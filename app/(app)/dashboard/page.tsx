import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { Suspense } from "react";
import { BusinessDashboard } from "@/components/dashboard/business-dashboard";
import { Page } from "@/components/layout/page";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/ui/kbd";
import { Skeleton } from "@/components/ui/skeleton";
import { $server } from "@/lib/api/server";
import { getQueryClient } from "@/lib/query/get-query-client";

export async function generateMetadata() {
  return { title: (await getTranslations("nav"))("dashboard") };
}

export default async function DashboardPage() {
  const [tNav, tCommon] = await Promise.all([getTranslations("nav"), getTranslations("common")]);
  const queryClient = getQueryClient();
  // Started, not awaited: the overview streams in when the API answers.
  void queryClient.prefetchQuery($server.queryOptions("get", "/v1/dashboard"));

  return (
    <Page
      title={tNav("dashboard")}
      className="max-w-[1440px] py-5"
      actions={
        <Button variant="primary" render={<Link href="/workflows/new" />}>
          <Plus />
          {tCommon("newWorkflow")}
          <Kbd className="ms-1">C</Kbd>
        </Button>
      }
    >
      <HydrationBoundary state={dehydrate(queryClient)}>
        <Suspense fallback={<Skeleton.Lines count={6} />}>
          <BusinessDashboard />
        </Suspense>
      </HydrationBoundary>
    </Page>
  );
}
