"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { browserFetch } from "@/lib/api/browser";

const REFRESH_MS = 30_000;

/** Liveness only: the check must not ping Postgres and Redis every 30 s. */
async function checkLive(): Promise<boolean> {
  const { data, response } = await browserFetch.GET("/v1/healthz/live");
  return response.ok && data?.status === "ok";
}

/** Says nothing while the API answers; a quiet line in the sidebar when it does not. */
export function BackendStatus() {
  const t = useTranslations("common");
  const { data: live, isError } = useQuery({
    queryKey: ["backend-live"],
    queryFn: checkLive,
    refetchInterval: REFRESH_MS,
    retry: false,
  });
  if (live !== false && !isError) return null;
  return (
    <p role="status" className="flex items-center gap-2 px-2 py-1 text-xs text-fail-ink">
      <span className="size-1.5 shrink-0 rounded-full bg-fail" aria-hidden />
      {t("backendOffline")}
    </p>
  );
}
