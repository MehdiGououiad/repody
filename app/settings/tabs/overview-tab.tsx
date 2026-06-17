"use client";

import { BrainCircuit, Gauge, ShieldCheck, Zap } from "lucide-react";
import { formatBytes, type PlatformConfig } from "@/lib/api/platform-config";
import type { OperatorStatus } from "@/lib/api/operator";
import { REPODY_VLM_LABEL } from "@/lib/document-model-branding";
import { MetricCard } from "../settings-shared";

export function OverviewTab({
  platform,
  operator,
}: {
  platform: PlatformConfig | null;
  operator: OperatorStatus | null;
}) {
  if (!platform) {
    return <div className="panel-elevated rounded-xl h-48 animate-pulse" />;
  }
  const defaultModelLabel =
    platform.documentModels.find((m) => m.id === platform.defaultOcrModel)?.label ??
    REPODY_VLM_LABEL;
  const runtimeRows = [
    ["Extractor", platform.extractor],
    ["Queue", platform.queueBackend],
    ["Inference", platform.inferenceMode],
    ["Storage", platform.storageBackend],
    ["Default model", defaultModelLabel],
    ["Read path", platform.defaultReadPath],
    ["LLM validation", platform.llmValidationEnabled ? "enabled" : "disabled"],
    ["Vision models", platform.documentModels.map((m) => m.label).join(", ") || "-"],
    ["Worker pools", Object.values(platform.workerPools).join(", ")],
    ["Upload limit", `${platform.maxUploadFiles} files / ${formatBytes(platform.maxUploadBytes)}`],
    ["Task timeout", `${platform.hatchetTaskTimeoutMinutes} min`],
  ];

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Execution"
          value={platform.queueBackend}
          detail={platform.hatchetConfigured ? "Queue configured" : "Queue needs attention"}
          Icon={Zap}
        />
        <MetricCard
          label="Extraction"
          value={platform.extractor}
          detail={`${defaultModelLabel} default`}
          Icon={BrainCircuit}
        />
        <MetricCard
          label="Cache"
          value={platform.cacheEnabled ? "Enabled" : "Disabled"}
          detail={platform.storageBackend}
          Icon={Gauge}
        />
        <MetricCard
          label="Operator actions"
          value={operator?.actionsEnabled ? "Enabled" : "Read only"}
          detail="Model and benchmark controls"
          Icon={ShieldCheck}
        />
      </div>

      <section className="panel-elevated rounded-xl overflow-hidden">
        <div className="px-6 py-5 border-b border-border bg-surface-container-low">
          <h2 className="font-display text-lg font-semibold">Effective runtime configuration</h2>
          <p className="text-sm text-on-surface-variant mt-1">
            Values currently used by the API and workers. Environment changes require a service restart.
          </p>
        </div>
        <dl className="grid sm:grid-cols-2 xl:grid-cols-3">
          {runtimeRows.map(([label, value]) => (
            <div key={label} className="px-6 py-4 border-b border-r border-border/70">
              <dt className="text-[11px] uppercase tracking-wider text-on-surface-variant">{label}</dt>
              <dd className="font-mono text-sm mt-1 break-words">{value}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}
