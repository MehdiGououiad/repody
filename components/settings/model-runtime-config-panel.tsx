"use client";

import { useMemo } from "react";
import { Info, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useModelRuntimeConfig } from "@/lib/hooks/use-catalog-queries";

type ConfigField = {
  key: string;
  envVar: string;
  label: string;
  description: string;
  scope: "platform" | "worker_runtime" | "inference_server";
  restart: string;
  value?: string | number | boolean | null;
  configured?: boolean;
  source?: string;
};

type RuntimeProfile = {
  modelId: string;
  label: string;
  runtime: string;
  runtimeModel: string;
  enabled: boolean;
  compareOnly?: boolean;
  inferenceUrl?: string | null;
  renderPolicy?: string;
  fields: ConfigField[];
};

const SCOPE_LABEL: Record<ConfigField["scope"], string> = {
  platform: "Platform env",
  worker_runtime: "Worker preprocessing",
  inference_server: "Host inference",
};

const RESTART_VARIANT: Record<string, "default" | "outline" | "secondary"> = {
  worker: "default",
  api: "secondary",
  inference: "outline",
  helm: "secondary",
  none: "outline",
};

function formatValue(value: ConfigField["value"]): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "true" : "false";
  return String(value);
}

function ConfigTable({ fields }: { fields: ConfigField[] }) {
  if (!fields.length) return null;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-[11px] uppercase tracking-wider text-on-surface-variant border-b border-border">
            <th className="py-2 pr-4 font-medium">Setting</th>
            <th className="py-2 pr-4 font-medium">Effective</th>
            <th className="py-2 pr-4 font-medium">Env var</th>
            <th className="py-2 pr-4 font-medium">Scope</th>
            <th className="py-2 font-medium">On change</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/70">
          {fields.map((field) => (
            <tr key={field.key} className="align-top">
              <td className="py-3 pr-4 min-w-[10rem]">
                <p className="font-medium">{field.label}</p>
                <p className="text-xs text-on-surface-variant mt-0.5 max-w-md">{field.description}</p>
              </td>
              <td className="py-3 pr-4 font-mono text-xs break-all">{formatValue(field.value)}</td>
              <td className="py-3 pr-4 font-mono text-xs text-on-surface-variant break-all">
                {field.envVar}
              </td>
              <td className="py-3 pr-4">
                <Badge variant="outline">{SCOPE_LABEL[field.scope]}</Badge>
              </td>
              <td className="py-3">
                <Badge variant={RESTART_VARIANT[field.restart] ?? "outline"}>{field.restart}</Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ModelRuntimeConfigPanel() {
  const query = useModelRuntimeConfig();
  const data = query.data;

  const profiles = useMemo<RuntimeProfile[]>(() => data?.models ?? [], [data?.models]);
  const shared = useMemo<ConfigField[]>(() => data?.shared ?? [], [data?.shared]);
  const notes = data?.deploymentNotes ?? [];

  return (
    <div className="space-y-6">
      <section className="panel-elevated rounded-xl overflow-hidden">
        <div className="px-6 py-5 border-b border-border bg-surface-container-low flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-display text-lg font-semibold">Model runtime configuration</h2>
            <p className="text-sm text-on-surface-variant mt-1">
              Single view of effective knobs per model. Platform values come from AUDIT_* env;
              host inference is configured outside the cluster.
            </p>
          </div>
          <Button variant="outline" onClick={() => void query.refetch()} disabled={query.isFetching}>
            <RefreshCw className={cn("h-4 w-4 mr-2", query.isFetching && "animate-spin")} />
            Refresh
          </Button>
        </div>

        {query.isLoading ? (
          <div className="h-40 animate-pulse" />
        ) : (
          <div className="divide-y divide-border">
            {profiles.map((profile) => (
              <div key={profile.modelId} className="px-6 py-5 space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-semibold">{profile.label}</h3>
                  <Badge variant={profile.enabled ? "success" : "danger"}>
                    {profile.enabled ? "Enabled" : "Disabled"}
                  </Badge>
                  {profile.compareOnly ? <Badge variant="outline">Benchmark only</Badge> : null}
                  <Badge variant="outline">{profile.runtime}</Badge>
                  <span className="text-xs font-mono text-on-surface-variant">{profile.modelId}</span>
                </div>
                <dl className="grid sm:grid-cols-2 gap-3 text-xs">
                  <div>
                    <dt className="text-on-surface-variant uppercase tracking-wider">Weights / catalog</dt>
                    <dd className="font-mono mt-0.5 break-all">{profile.runtimeModel}</dd>
                  </div>
                  <div>
                    <dt className="text-on-surface-variant uppercase tracking-wider">Inference URL</dt>
                    <dd className="font-mono mt-0.5 break-all">{profile.inferenceUrl || "—"}</dd>
                  </div>
                  {profile.renderPolicy ? (
                    <div className="sm:col-span-2">
                      <dt className="text-on-surface-variant uppercase tracking-wider">Input policy (upstream docs)</dt>
                      <dd className="mt-0.5 text-on-surface-variant">{profile.renderPolicy}</dd>
                    </div>
                  ) : null}
                </dl>
                <ConfigTable fields={profile.fields} />
              </div>
            ))}

            {shared.length ? (
              <div className="px-6 py-5 space-y-3">
                <h3 className="font-semibold">Shared document limits</h3>
                <ConfigTable fields={shared} />
              </div>
            ) : null}
          </div>
        )}
      </section>

      {notes.length ? (
        <section className="panel-elevated rounded-xl p-6 space-y-4">
          <div className="flex items-start gap-3">
            <span className="size-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0">
              <Info className="h-5 w-5" />
            </span>
            <div className="space-y-3 flex-1">
              <div>
                <h2 className="font-display text-lg font-semibold">What needs a rebuild?</h2>
                <p className="text-sm text-on-surface-variant mt-1">
                  Config on this page is env-driven. Code changes still require image rebuilds.
                </p>
              </div>
              <div className="space-y-3">
                {notes.map((note) => (
                  <div key={note.changeKind} className="rounded-lg border border-border bg-surface-container-low px-4 py-3">
                    <p className="font-medium text-sm">{note.changeKind}</p>
                    <p className="text-sm text-primary mt-0.5">{note.action}</p>
                    <p className="text-xs text-on-surface-variant mt-1">{note.detail}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      ) : null}
    </div>
  );
}
