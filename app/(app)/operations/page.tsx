import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { getTranslations } from "next-intl/server";
import { Suspense } from "react";
import { Page } from "@/components/layout/page";
import { ControlRoom } from "@/components/operations/control-room";
import { Skeleton } from "@/components/ui/skeleton";
import { $server } from "@/lib/api/server";
import { getQueryClient } from "@/lib/query/get-query-client";

export async function generateMetadata() {
  return { title: (await getTranslations("nav"))("operations") };
}

export default async function OperationsPage() {
  const [tNav, t] = await Promise.all([getTranslations("nav"), getTranslations("operations")]);
  const queryClient = getQueryClient();
  void queryClient.prefetchQuery($server.queryOptions("get", "/v1/operations"));

  return (
    <Page
      title={tNav("operations")}
      className="max-w-[1440px] py-5"
      status={
        <span className="flex h-5 items-center gap-1.5 rounded-full bg-pass-wash px-2 text-xs font-medium text-pass-ink">
          <span className="relative flex size-1.5">
            <span className="absolute inset-0 animate-ping rounded-full bg-pass opacity-60 motion-reduce:hidden" />
            <span className="relative size-1.5 rounded-full bg-pass" />
          </span>
          {t("live")}
        </span>
      }
    >
      <HydrationBoundary state={dehydrate(queryClient)}>
        <Suspense fallback={<Skeleton.Lines count={6} />}>
          <ControlRoom />
        </Suspense>
      </HydrationBoundary>
    </Page>
  );
}
