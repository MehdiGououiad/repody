import { BrainCircuit, Gauge, type LucideIcon, ServerCog, Zap } from "lucide-react";
import type { PlatformConfig } from "@/lib/api/platform-config";
import type { ModelsCatalogResponse } from "@/lib/api/schema-types";
import { formatBytes } from "@/lib/utils";

function MetricCard({
  label,
  value,
  detail,
  Icon,
}: {
  label: string;
  value: string;
  detail: string;
  Icon: LucideIcon;
}) {
  return (
    <div className="panel-elevated rounded-xl p-5 min-w-0">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-on-surface-variant">
          {label}
        </p>
        <span className="size-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
          <Icon className="h-4 w-4" aria-hidden="true" />
        </span>
      </div>
      <p className="mt-4 text-2xl font-display font-semibold text-on-surface truncate">{value}</p>
      <p className="mt-1 text-xs text-on-surface-variant">{detail}</p>
    </div>
  );
}

/** Read-only platform configuration and document-model status (no operator actions). */
export function PlatformOverview({
  platform,
  catalog,
}: {
  platform: PlatformConfig;
  catalog: ModelsCatalogResponse | null;
}) {
  const model = catalog?.models[0];
  const modelState = !model ? "Unknown" : model.available ? "Ready" : "Unavailable";
  const runtimeRows = [
    ["Queue", platform.queueBackend],
    ["Inference endpoint", platform.llamacppBaseUrl],
    ["Served model", platform.servedModel],
    ["Worker pools", Object.values(platform.workerPools).join(", ")],
    ["Upload limit", `${platform.maxUploadFiles} files / ${formatBytes(platform.maxUploadBytes)}`],
    ["Task timeout", `${platform.workerTaskTimeoutMinutes} min`],
  ];

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Document model"
          value={modelState}
          detail={model?.availabilityNote ?? model?.label ?? platform.servedModel}
          Icon={BrainCircuit}
        />
        <MetricCard
          label="Execution"
          value={platform.queueBackend}
          detail={platform.taskiqConfigured ? "Queue configured" : "Queue needs attention"}
          Icon={Zap}
        />
        <MetricCard
          label="Cache"
          value={platform.cacheEnabled ? "Enabled" : "Disabled"}
          detail="Redis extraction cache"
          Icon={Gauge}
        />
        <MetricCard
          label="Rate limit"
          value={platform.rateLimitEnabled ? "Enabled" : "Off"}
          detail="API request limits"
          Icon={ServerCog}
        />
      </div>

      <section className="panel-elevated rounded-xl overflow-hidden">
        <div className="px-6 py-5 border-b border-border bg-surface-container-low">
          <h2 className="font-display text-lg font-semibold">Effective runtime configuration</h2>
          <p className="text-sm text-on-surface-variant mt-1">
            Values currently used by the API and workers. Environment changes require a service
            restart.
          </p>
        </div>
        <dl className="grid sm:grid-cols-2 xl:grid-cols-3">
          {runtimeRows.map(([label, value]) => (
            <div key={label} className="px-6 py-4 border-b border-r border-border/70">
              <dt className="text-[11px] uppercase tracking-wider text-on-surface-variant">
                {label}
              </dt>
              <dd className="font-mono text-sm mt-1 break-words">{value}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}
