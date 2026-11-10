"use client";

import { useQuery } from "@tanstack/react-query";
import { Circle, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { browserFetch } from "@/lib/api/browser";
import { cn } from "@/lib/utils";

const REFRESH_MS = 30_000;

/** Liveness only: the badge must not ping Postgres and Redis every 30 s. */
async function checkLive(): Promise<{ ok: boolean; latencyMs: number }> {
  const started = performance.now();
  const { data, response } = await browserFetch.GET("/v1/healthz/live");
  return {
    ok: response.ok && data?.status === "ok",
    latencyMs: Math.round(performance.now() - started),
  };
}

export function BackendStatus() {
  const t = useTranslations("common");
  const { data, isError, isPending } = useQuery({
    queryKey: ["backend-live"],
    queryFn: checkLive,
    refetchInterval: REFRESH_MS,
    retry: false,
  });
  const status = isPending ? "checking" : isError || !data?.ok ? "down" : "ok";
  const label =
    status === "ok"
      ? t("backendOnline", { ms: data?.latencyMs ?? 0 })
      : status === "checking"
        ? t("backendChecking")
        : t("backendOffline");

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={cn(
              "hidden sm:flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-medium",
              status === "ok" && "border-success/30 bg-success/5 text-success",
              status === "down" && "border-danger/30 bg-danger/5 text-danger",
              status === "checking" &&
                "border-border bg-surface-container-low text-on-surface-variant"
            )}
          >
            {status === "checking" ? (
              <Loader2 className="h-2.5 w-2.5 animate-spin" />
            ) : (
              <Circle className="h-2 w-2 fill-current" />
            )}
            {t("backendLabel")}
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom">{label}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
