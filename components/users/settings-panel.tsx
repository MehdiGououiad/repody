"use client";

import { AlertTriangle, BrainCircuit, ExternalLink, FileCheck2, KeyRound, RefreshCw, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { IamCatalog, IamMe } from "@/lib/api/iam";
import { formatBytes, type PlatformConfig } from "@/lib/api/platform-config";
import { REPODY_VLM_LABEL } from "@/lib/document-model-branding";
import { cn } from "@/lib/utils";
import { ConfigTable, SettingMetric, StatusLine } from "./user-access-shared";

export function SettingsPanel({
  me,
  catalog,
  platform,
  platformError,
  onRefresh,
  refreshing,
}: {
  me: IamMe | null;
  catalog: IamCatalog | null;
  platform: PlatformConfig | null;
  platformError: string | null;
  onRefresh: () => void;
  refreshing: boolean;
}) {
  const defaultModelLabel =
    platform?.documentModels.find((model) => model.id === platform.defaultDocumentModelId)?.label ??
    REPODY_VLM_LABEL;
  const roleCount = catalog?.appRoles.length ?? 0;
  const permissionCount =
    catalog?.roles.reduce((total, role) => total + role.permissions.length, 0) ?? 0;

  const identityRows: Array<[string, string]> = [
    ["OIDC", me?.oidcEnabled ? "enabled" : "disabled"],
    ["Signed-in subject", me?.subject ?? "-"],
    ["Current roles", me?.roles.join(", ") || "-"],
    ["Keycloak admin", me?.keycloakAdminUrl ?? "not configured"],
  ];

  const runtimeRows: Array<[string, string]> = platform
    ? [
        ["App", platform.appName],
        ["Extractor", platform.extractor],
        ["Inference mode", platform.inferenceMode],
        ["Storage", platform.storageBackend],
        ["Queue", platform.queueBackend],
        ["Default model", defaultModelLabel],
        ["Read path", platform.defaultReadPath],
        [
          "Worker pools",
          Object.entries(platform.workerPools)
            .map(([key, value]) => `${key}: ${value}`)
            .join(", "),
        ],
      ]
    : [];

  const limitsRows: Array<[string, string]> = platform
    ? [
        ["Upload size", formatBytes(platform.maxUploadBytes)],
        ["Upload files", `${platform.maxUploadFiles}`],
        ["NuExtract max pages", `${platform.nuextractMaxPagesPerRequest}`],
        ["Task timeout", `${platform.workerTaskTimeoutMinutes} min`],
        ["Stale run timeout", `${platform.staleRunTimeoutMinutes} min`],
        ["Queued stale timeout", `${platform.queuedStaleTimeoutMinutes} min`],
        ["Maintenance interval", `${platform.maintenanceIntervalSeconds}s`],
      ]
    : [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 rounded-xl border border-border bg-surface-container-low px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h2 className="font-display text-lg font-semibold">Access and platform settings</h2>
          <p className="mt-1 text-sm text-on-surface-variant">
            Read-only effective settings used by the web app, API, workers, and identity provider.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {me?.keycloakAdminUrl ? (
            <Button variant="outline" size="sm" asChild className="gap-2">
              <a href={me.keycloakAdminUrl} target="_blank" rel="noreferrer">
                <ExternalLink className="h-3.5 w-3.5" />
                Keycloak
              </a>
            </Button>
          ) : null}
          <Button variant="outline" size="sm" onClick={onRefresh} disabled={refreshing} className="gap-2">
            <RefreshCw className={cn("h-3.5 w-3.5", refreshing && "animate-spin")} />
            Refresh
          </Button>
        </div>
      </div>

      {platformError ? (
        <div className="rounded-xl border border-warning/30 bg-warning-soft px-4 py-3 text-sm text-warning-strong">
          {platformError}
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SettingMetric
          label="Identity"
          value={me?.oidcEnabled ? "OIDC" : "Dev mode"}
          detail={me?.email ?? "Local principal"}
          icon={KeyRound}
          tone={me?.oidcEnabled ? "success" : "warning"}
        />
        <SettingMetric
          label="Roles"
          value={`${roleCount}`}
          detail={`${permissionCount} permission grants`}
          icon={ShieldCheck}
          tone="success"
        />
        <SettingMetric
          label="Runtime"
          value={platform?.inferenceMode ?? "-"}
          detail={platform ? `${platform.extractor} extraction` : "Platform config unavailable"}
          icon={BrainCircuit}
        />
        <SettingMetric
          label="Uploads"
          value={platform ? formatBytes(platform.maxUploadBytes) : "-"}
          detail={platform ? `${platform.maxUploadFiles} files per batch` : "Upload limits unavailable"}
          icon={FileCheck2}
        />
      </div>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <div className="panel-elevated overflow-hidden rounded-xl">
          <div className="border-b border-border bg-surface-container-low px-6 py-5">
            <h3 className="font-display text-lg font-semibold">Security posture</h3>
            <p className="mt-1 text-sm text-on-surface-variant">
              Current guardrails that affect sign-in, authorization, uploads, and request handling.
            </p>
          </div>
          <StatusLine
            label="OIDC authentication"
            value={me?.oidcEnabled ? "enabled" : "off"}
            enabled={!!me?.oidcEnabled}
            detail="Human sessions use Keycloak access tokens and backend RBAC validates every protected API call."
          />
          <StatusLine
            label="User management"
            value={me?.canManageUsers ? "allowed" : "read only"}
            enabled={!!me?.canManageUsers}
            detail="Only principals with users:write can invite users, change status, reset passwords, or update roles."
          />
          <StatusLine
            label="Rate limiting"
            value={platform?.rateLimitEnabled ? "enabled" : "off"}
            enabled={!!platform?.rateLimitEnabled}
            detail="Global API rate limiting reduces abuse risk on authenticated and public endpoints."
          />
          <StatusLine
            label="Direct uploads"
            value={platform?.directUploadEnabled ? "enabled" : "proxied"}
            enabled={!!platform?.directUploadEnabled}
            detail="Direct object-store uploads are only active when S3-compatible storage and presigning are available."
          />
        </div>

        <div className="panel-elevated overflow-hidden rounded-xl">
          <div className="border-b border-border bg-surface-container-low px-6 py-5">
            <h3 className="font-display text-lg font-semibold">Reviewer checklist</h3>
            <p className="mt-1 text-sm text-on-surface-variant">
              Settings that external reviewers usually expect to inspect before production rollout.
            </p>
          </div>
          <div className="divide-y divide-border/70">
            {[
              ["Least privilege", "Keep platform_admin limited to break-glass users; prefer admin/operator/viewer for normal work."],
              ["Session scope", "Offline Keycloak tokens stay opt-in; normal auth-code refresh tokens are used by default."],
              ["Runtime evidence", "Use diagnostics and benchmark tabs to capture CPU/GPU readiness before switching inference modes."],
              ["Upload safety", "Review MIME allowlists, file count, and max size with the backend upload validation tests."],
            ].map(([title, body]) => (
              <div key={title} className="flex gap-3 px-5 py-4">
                <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <AlertTriangle className="h-4 w-4" aria-hidden="true" />
                </span>
                <div>
                  <p className="text-sm font-semibold">{title}</p>
                  <p className="mt-1 text-xs leading-relaxed text-on-surface-variant">{body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="grid gap-4 xl:grid-cols-2">
        <ConfigTable
          title="Identity configuration"
          description="Effective identity state for the current session and admin console."
          rows={identityRows}
        />
        <ConfigTable
          title="Runtime configuration"
          description="Read-only API and worker settings. Environment changes require service restart."
          rows={runtimeRows}
        />
        <ConfigTable
          title="Limits and timeouts"
          description="Operational limits that affect uploads, extraction, queue maintenance, and stuck-run recovery."
          rows={limitsRows}
        />
        <section className="panel-elevated overflow-hidden rounded-xl">
          <div className="border-b border-border bg-surface-container-low px-6 py-5">
            <h3 className="font-display text-lg font-semibold">Platform switches</h3>
            <p className="mt-1 text-sm text-on-surface-variant">
              Feature flags currently exposed by the backend settings snapshot.
            </p>
          </div>
          <StatusLine
            label="Extraction cache"
            value={platform?.cacheEnabled ? "enabled" : "off"}
            enabled={!!platform?.cacheEnabled}
            detail="Caches repeated extraction work where the backend storage strategy supports it."
          />
          <StatusLine
            label="GPU live probe"
            value={platform?.gpuLiveProbe ? "enabled" : "off"}
            enabled={!!platform?.gpuLiveProbe}
            detail="Allows health checks and diagnostics to perform live inference probes when enabled."
          />
        </section>
      </div>
    </div>
  );
}
