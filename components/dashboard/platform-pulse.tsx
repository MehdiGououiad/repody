import Link from "next/link";
import {
  Activity,
  BrainCircuit,
  Layers,
  ListOrdered,
  ArrowUpRight,
} from "lucide-react";
import { getTranslations } from "next-intl/server";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { REPODY_VLM_LABEL } from "@/lib/document-model-branding";
import type { PlatformConfig } from "@/lib/api/platform-config";
import type { PlatformHealth } from "@/lib/api/dashboard";
import type { OperatorStatus } from "@/lib/api/operator";
import { cn } from "@/lib/utils";

function PulseCard({
  label,
  value,
  detail,
  tone = "default",
}: {
  label: string;
  value: string;
  detail: string;
  tone?: "default" | "success" | "warning" | "danger";
}) {
  const toneClass = {
    default: "text-on-surface",
    success: "text-success",
    warning: "text-warning",
    danger: "text-danger",
  }[tone];

  return (
    <div className="panel-elevated rounded-xl p-4 min-w-0">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
        {label}
      </p>
      <p className={cn("mt-2 text-xl font-display font-semibold truncate", toneClass)}>{value}</p>
      <p className="mt-1 text-xs text-on-surface-variant leading-relaxed">{detail}</p>
    </div>
  );
}

export async function PlatformPulse({
  healthz,
  platform,
  operator,
}: {
  healthz: PlatformHealth | null;
  platform: PlatformConfig | null;
  operator: OperatorStatus | null;
}) {
  const t = await getTranslations("dashboard.platform");

  if (!healthz && !platform) return null;

  const defaultModel =
    platform?.documentModels.find((m) => m.id === platform.defaultOcrModel)?.label ??
    REPODY_VLM_LABEL;
  const queued = healthz?.queuedRuns ?? 0;
  const inflight = healthz?.inflightRuns ?? 0;
  const queueTotal = queued + inflight;
  const hatchetOk = healthz?.hatchetConfigured ?? platform?.hatchetConfigured ?? false;

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-base font-semibold text-on-surface">{t("title")}</h2>
          <p className="text-xs text-on-surface-variant mt-0.5">{t("hint")}</p>
        </div>
        <Link href="/settings?tab=diagnostics">
          <Button variant="ghost" size="sm" className="h-8 gap-1.5 text-xs">
            {t("openConsole")}
            <ArrowUpRight className="h-3.5 w-3.5" />
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <PulseCard
          label={t("queue")}
          value={String(queueTotal)}
          detail={
            queueTotal > 0
              ? t("queueDetail", { queued, inflight })
              : t("queueIdle")
          }
          tone={queued > 5 ? "warning" : "default"}
        />
        <PulseCard
          label={t("workers")}
          value={hatchetOk ? t("workersReady") : t("workersAttention")}
          detail={
            healthz
              ? `fast: ${healthz.workerPools.fast ?? "—"} · ocr: ${healthz.workerPools.ocr ?? "—"}`
              : platform
                ? Object.values(platform.workerPools).join(" · ")
                : "—"
          }
          tone={hatchetOk ? "success" : "warning"}
        />
        <PulseCard
          label={t("extraction")}
          value={platform?.extractor ?? healthz?.extractor ?? "—"}
          detail={`${defaultModel} · ${platform?.inferenceMode ?? healthz?.inference ?? "—"}`}
        />
        <PulseCard
          label={t("operator")}
          value={operator?.actionsEnabled ? t("operatorOn") : t("operatorReadOnly")}
          detail={
            platform?.cacheEnabled
              ? t("cacheOn", { backend: platform.storageBackend })
              : t("cacheOff")
          }
          tone={operator?.actionsEnabled ? "success" : "default"}
        />
      </div>

      <div className="flex flex-wrap gap-2">
        <Badge variant={healthz?.status === "ok" ? "success" : "outline"} className="gap-1.5">
          <Activity className="h-3 w-3" />
          API {healthz?.status === "ok" ? t("statusOk") : t("statusUnknown")}
        </Badge>
        {platform ? (
          <Badge variant="outline" className="gap-1.5">
            <Layers className="h-3 w-3" />
            {platform.queueBackend}
          </Badge>
        ) : null}
        {platform ? (
          <Badge variant="outline" className="gap-1.5">
            <BrainCircuit className="h-3 w-3" />
            {platform.llmValidationEnabled ? t("llmOn") : t("llmOff")}
          </Badge>
        ) : null}
        {queueTotal > 0 ? (
          <Badge variant="outline" className="gap-1.5">
            <ListOrdered className="h-3 w-3" />
            {t("runsInPipeline", { count: queueTotal })}
          </Badge>
        ) : null}
      </div>
    </section>
  );
}
