"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { browserFetch } from "@/lib/api/browser";
import { useHasModule } from "@/modules/core/entitlement-context";

const REFRESH_MS = 30_000;

/** Liveness only: probes the active module service without hitting Postgres every 30s. */
async function checkLive(hasIdp: boolean): Promise<boolean> {
  if (hasIdp) {
    const { data, response } = await browserFetch.GET("/v1/healthz/live");
    return response.ok && data?.status === "ok";
  }
  const response = await fetch("/api/fraud/v1/healthz/live", { cache: "no-store" });
  return response.ok;
}

/** Says nothing while the active API answers; a quiet line in the sidebar when offline. */
export function BackendStatus() {
  const t = useTranslations("common");
  const hasIdp = useHasModule("idp");
  const hasFraud = useHasModule("fraud");

  const { data: live, isError } = useQuery({
    queryKey: ["backend-live", hasIdp, hasFraud],
    queryFn: () => checkLive(hasIdp),
    refetchInterval: REFRESH_MS,
    retry: false,
    enabled: hasIdp || hasFraud,
  });
  if (!hasIdp && !hasFraud) return null;
  if (live !== false && !isError) return null;
  return (
    // oxlint-disable-next-line jsx-a11y/prefer-tag-over-role -- a live region (ARIA status), not the result of a calculation (<output>).
    <p role="status" className="flex items-center gap-2 px-2 py-1 text-xs text-fail-ink">
      <span className="size-1.5 shrink-0 rounded-full bg-fail" aria-hidden />
      {t("backendOffline")}
    </p>
  );
}
