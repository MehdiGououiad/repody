"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Circle, Loader2 } from "lucide-react";
import { checkBackendHealth, type BackendHealth } from "@/lib/api/health";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function BackendStatus() {
  const t = useTranslations("common");
  const [health, setHealth] = useState<BackendHealth>({ status: "checking" });

  useEffect(() => {
    let mounted = true;
    const run = async () => {
      const h = await checkBackendHealth();
      if (mounted) setHealth(h);
    };
    run();
    const id = setInterval(run, 30_000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  const label =
    health.status === "ok"
      ? t("backendOnline", { ms: health.latencyMs ?? 0 })
      : health.status === "checking"
        ? t("backendChecking")
        : t("backendOffline");

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={cn(
              "hidden sm:flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-medium",
              health.status === "ok" &&
                "border-success/30 bg-success/5 text-success",
              health.status === "down" &&
                "border-danger/30 bg-danger/5 text-danger",
              health.status === "checking" &&
                "border-border bg-surface-container-low text-on-surface-variant"
            )}
          >
            {health.status === "checking" ? (
              <Loader2 className="h-2.5 w-2.5 animate-spin" />
            ) : (
              <Circle
                className={cn(
                  "h-2 w-2 fill-current",
                  health.status === "ok" && "text-success",
                  health.status === "down" && "text-danger"
                )}
              />
            )}
            {t("backendLabel")}
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom">{label}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
