"use client";

import { CheckCircle2, CircleAlert, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import type { PlatformConfig } from "@/lib/api/platform-config";
import type { OperatorJob, OperatorStatus } from "@/lib/api/operator";
import { ACTIVE_STATUSES, StatusBadge } from "../settings-shared";

export function DiagnosticsTab({
  platform,
  operator,
  jobs,
  onRefresh,
}: {
  platform: PlatformConfig | null;
  operator: OperatorStatus | null;
  jobs: OperatorJob[];
  onRefresh: () => void;
}) {
  const checks = [
    {
      label: "API configuration",
      ok: !!platform,
      detail: platform ? `${platform.appName} is responding` : "Platform configuration unavailable",
    },
    {
      label: "Queue dispatch",
      ok: !!platform?.taskiqConfigured,
      detail: platform?.taskiqConfigured ? `${platform.queueBackend} is configured` : "Queue is not configured",
    },
    {
      label: "Operator controls",
      ok: !!operator?.actionsEnabled,
      detail: operator?.actionsEnabled ? "Expensive actions are enabled" : "Console is read only",
    },
    {
      label: "Extraction cache",
      ok: !!platform?.cacheEnabled,
      detail: platform?.cacheEnabled ? "Cache is active" : "Cache is disabled",
    },
  ];

  return (
    <div className="grid xl:grid-cols-[1fr_420px] gap-6">
      <section className="panel-elevated rounded-xl overflow-hidden">
        <div className="px-6 py-5 border-b border-border bg-surface-container-low flex items-center justify-between gap-3">
          <div>
            <h2 className="font-display text-lg font-semibold">System checks</h2>
            <p className="text-sm text-on-surface-variant mt-1">Live configuration and readiness signals.</p>
          </div>
          <Button variant="outline" onClick={onRefresh}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
        <div className="divide-y divide-border">
          {checks.map((check) => (
            <div key={check.label} className="px-6 py-4 flex items-center gap-4">
              {check.ok ? (
                <CheckCircle2 className="h-5 w-5 text-success shrink-0" />
              ) : (
                <CircleAlert className="h-5 w-5 text-warning shrink-0" />
              )}
              <div>
                <p className="text-sm font-semibold">{check.label}</p>
                <p className="text-xs text-on-surface-variant mt-0.5">{check.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </section>
      <section className="panel-elevated rounded-xl overflow-hidden">
        <div className="px-6 py-5 border-b border-border bg-surface-container-low">
          <h2 className="font-display text-lg font-semibold">Operator jobs</h2>
          <p className="text-sm text-on-surface-variant mt-1">Recent model and benchmark activity.</p>
        </div>
        <div className="divide-y divide-border max-h-[560px] overflow-y-auto">
          {jobs.length === 0 ? (
            <p className="p-6 text-sm text-on-surface-variant">No operator jobs yet.</p>
          ) : jobs.map((job) => (
            <div key={job.id} className="p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold">{job.label}</p>
                  <p className="text-[11px] text-on-surface-variant mt-1">
                    {new Date(job.createdAt).toLocaleString()}
                  </p>
                </div>
                <StatusBadge status={job.status} />
              </div>
              {job.progress ? <p className="text-xs text-on-surface-variant mt-3 break-words">{job.progress}</p> : null}
              {job.error ? <p className="text-xs text-danger mt-2">{job.error}</p> : null}
              {ACTIVE_STATUSES.has(job.status) ? <Progress value={job.status === "queued" ? 15 : 55} className="mt-3 h-1.5" /> : null}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
