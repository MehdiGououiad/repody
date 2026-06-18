"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BrainCircuit,
  Database,
  ExternalLink,
  FileCheck2,
  Gauge,
  KeyRound,
  LoaderCircle,
  Plus,
  RefreshCw,
  Search,
  Settings,
  Shield,
  ShieldCheck,
  SlidersHorizontal,
  UserCog,
  Users,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  createIamUser,
  fetchIamCatalog,
  fetchIamMe,
  fetchIamUsers,
  updateIamUser,
  type IamCatalog,
  type IamMe,
  type IamUser,
} from "@/lib/api/iam";
import { fetchPlatformConfig, formatBytes, type PlatformConfig } from "@/lib/api/platform-config";
import { REPODY_VLM_LABEL } from "@/lib/document-model-branding";
import { cn } from "@/lib/utils";

const ROLE_BADGE: Record<string, "default" | "secondary" | "info" | "outline"> = {
  platform_admin: "default",
  admin: "default",
  operator: "info",
  viewer: "secondary",
};

function displayName(user: IamUser) {
  const full = [user.firstName, user.lastName].filter(Boolean).join(" ").trim();
  return full || user.email || user.username;
}

function RoleBadges({ roles }: { roles: string[] }) {
  return (
    <div className="flex flex-wrap gap-1">
      {roles.map((role) => (
        <Badge key={role} variant={ROLE_BADGE[role] ?? "outline"} className="text-[10px] font-medium">
          {role}
        </Badge>
      ))}
    </div>
  );
}

function RolePicker({
  appRoles,
  catalog,
  value,
  onChange,
}: {
  appRoles: string[];
  catalog: IamCatalog | null;
  value: string[];
  onChange: (roles: string[]) => void;
}) {
  const toggle = (role: string) => {
    if (value.includes(role)) {
      if (value.length === 1) return;
      onChange(value.filter((item) => item !== role));
      return;
    }
    onChange([...value, role]);
  };

  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {appRoles.map((roleId) => {
        const meta = catalog?.roles.find((role) => role.id === roleId);
        const selected = value.includes(roleId);
        return (
          <button
            key={roleId}
            type="button"
            onClick={() => toggle(roleId)}
            className={cn(
              "rounded-xl border px-3 py-2.5 text-left transition-colors",
              selected
                ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                : "border-border hover:border-outline-variant hover:bg-surface-bright"
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-semibold">{meta?.label ?? roleId}</span>
              {selected ? <ShieldCheck className="h-4 w-4 text-primary" /> : null}
            </div>
            <p className="mt-1 text-[11px] leading-relaxed text-on-surface-variant">
              {meta?.description}
            </p>
          </button>
        );
      })}
    </div>
  );
}

function PermissionMatrix({ catalog }: { catalog: IamCatalog | null }) {
  const rows = useMemo(() => {
    if (!catalog) return [];
    const keys = new Set<string>();
    for (const role of catalog.roles) {
      for (const grant of role.permissions) {
        keys.add(`${grant.resource}:${grant.action}`);
      }
    }
    return [...keys]
      .sort()
      .map((key) => {
        const [resource, action] = key.split(":");
        const byRole: Record<string, boolean> = {};
        for (const role of catalog.roles) {
          byRole[role.id] = role.permissions.some(
            (grant) => grant.resource === resource && grant.action === action
          );
        }
        return { resource, action, byRole };
      });
  }, [catalog]);

  if (!catalog) {
    return <div className="panel-elevated rounded-xl h-40 animate-pulse" />;
  }

  return (
    <section className="panel-elevated rounded-xl overflow-hidden">
      <div className="px-6 py-5 border-b border-border bg-surface-container-low">
        <h2 className="font-display text-lg font-semibold">Role permissions</h2>
        <p className="text-sm text-on-surface-variant mt-1">
          Static Casbin policy enforced on every API request. Roles are assigned in Keycloak.
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="border-b border-border bg-surface-container-lowest/80">
              <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">
                Permission
              </th>
              {catalog.roles.map((role) => (
                <th
                  key={role.id}
                  className="px-3 py-3 text-center text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant"
                >
                  {role.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.resource}:${row.action}`} className="border-b border-border/70">
                <td className="px-4 py-3 font-mono text-xs">
                  <span className="text-on-surface">{row.resource}</span>
                  <span className="text-on-surface-variant">:</span>
                  <span className="text-primary">{row.action}</span>
                </td>
                {catalog.roles.map((role) => (
                  <td key={role.id} className="px-3 py-3 text-center">
                    {row.byRole[role.id] ? (
                      <ShieldCheck className="inline h-4 w-4 text-success" aria-label="allowed" />
                    ) : (
                      <span className="text-on-surface-variant/30">—</span>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function SettingMetric({
  label,
  value,
  detail,
  icon: Icon,
  tone = "info",
}: {
  label: string;
  value: string;
  detail: string;
  icon: typeof Settings;
  tone?: "info" | "success" | "warning";
}) {
  const toneClass = {
    info: "bg-info-soft text-info",
    success: "bg-success-soft text-success-strong",
    warning: "bg-warning-soft text-warning-strong",
  }[tone];

  return (
    <div className="panel-elevated rounded-xl p-5 min-w-0">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-on-surface-variant">
          {label}
        </p>
        <span className={cn("size-9 rounded-lg flex items-center justify-center", toneClass)}>
          <Icon className="h-4 w-4" aria-hidden="true" />
        </span>
      </div>
      <p className="mt-4 text-2xl font-display font-semibold text-on-surface truncate">{value}</p>
      <p className="mt-1 text-xs text-on-surface-variant">{detail}</p>
    </div>
  );
}

function StatusLine({
  label,
  value,
  enabled,
  detail,
}: {
  label: string;
  value: string;
  enabled: boolean;
  detail: string;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-border/70 px-5 py-4 last:border-b-0">
      <div className="min-w-0">
        <p className="text-sm font-medium text-on-surface">{label}</p>
        <p className="mt-1 text-xs leading-relaxed text-on-surface-variant">{detail}</p>
      </div>
      <Badge variant={enabled ? "success" : "outline"} withDot className="shrink-0">
        {value}
      </Badge>
    </div>
  );
}

function ConfigTable({
  title,
  description,
  rows,
}: {
  title: string;
  description: string;
  rows: Array<[string, string]>;
}) {
  return (
    <section className="panel-elevated rounded-xl overflow-hidden">
      <div className="border-b border-border bg-surface-container-low px-6 py-5">
        <h3 className="font-display text-lg font-semibold">{title}</h3>
        <p className="mt-1 text-sm text-on-surface-variant">{description}</p>
      </div>
      <dl className="grid sm:grid-cols-2">
        {rows.map(([label, value]) => (
          <div key={label} className="border-b border-r border-border/70 px-5 py-4 min-w-0">
            <dt className="text-[11px] uppercase tracking-wider text-on-surface-variant">{label}</dt>
            <dd className="mt-1 break-words font-mono text-sm text-on-surface">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function SettingsPanel({
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
    platform?.documentModels.find((model) => model.id === platform.defaultOcrModel)?.label ??
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
        ["Worker pools", Object.entries(platform.workerPools).map(([key, value]) => `${key}: ${value}`).join(", ")],
      ]
    : [];

  const limitsRows: Array<[string, string]> = platform
    ? [
        ["Upload size", formatBytes(platform.maxUploadBytes)],
        ["Upload files", `${platform.maxUploadFiles}`],
        ["OCR max pages", `${platform.ocrMaxPages}`],
        ["Task timeout", `${platform.hatchetTaskTimeoutMinutes} min`],
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
        <div className="panel-elevated rounded-xl overflow-hidden">
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

        <div className="panel-elevated rounded-xl overflow-hidden">
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
          description="Operational limits that affect uploads, OCR, queue maintenance, and stuck-run recovery."
          rows={limitsRows}
        />
        <section className="panel-elevated rounded-xl overflow-hidden">
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
            label="Structured LLM output"
            value={platform?.structuredLlm ? "enabled" : "off"}
            enabled={!!platform?.structuredLlm}
            detail="Requests structured validation output from compatible LLM providers."
          />
          <StatusLine
            label="LLM validation"
            value={platform?.llmValidationEnabled ? "enabled" : "off"}
            enabled={!!platform?.llmValidationEnabled}
            detail="Controls whether extracted document facts are validated through the configured LLM path."
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

export function UsersPage() {
  const [me, setMe] = useState<IamMe | null>(null);
  const [catalog, setCatalog] = useState<IamCatalog | null>(null);
  const [platform, setPlatform] = useState<PlatformConfig | null>(null);
  const [platformError, setPlatformError] = useState<string | null>(null);
  const [usersState, setUsersState] = useState<{
    users: IamUser[];
    managementAvailable: boolean;
    managementError?: string | null;
  } | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [settingsRefreshing, setSettingsRefreshing] = useState(false);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [editUser, setEditUser] = useState<IamUser | null>(null);
  const [saving, setSaving] = useState(false);

  const [inviteForm, setInviteForm] = useState({
    email: "",
    firstName: "",
    lastName: "",
    password: "",
    roles: ["viewer"] as string[],
  });
  const [editForm, setEditForm] = useState({
    firstName: "",
    lastName: "",
    enabled: true,
    roles: [] as string[],
    password: "",
  });

  const load = useCallback(async (query?: string) => {
    const [nextMe, nextCatalog, nextUsers, nextPlatform] = await Promise.all([
      fetchIamMe(),
      fetchIamCatalog().catch(() => null),
      fetchIamUsers(query).catch((error) => ({
        users: [],
        managementAvailable: false,
        managementError: error instanceof Error ? error.message : "Could not list users.",
      })),
      fetchPlatformConfig()
        .then((data) => ({ data, error: null }))
        .catch((error) => ({
          data: null,
          error: error instanceof Error ? error.message : "Could not load platform settings.",
        })),
    ]);
    setMe(nextMe);
    setCatalog(nextCatalog);
    setUsersState(nextUsers);
    setPlatform(nextPlatform.data);
    setPlatformError(nextPlatform.error);
  }, []);

  useEffect(() => {
    let active = true;

    void Promise.resolve()
      .then(() => load())
      .catch((error) => {
        toast.error(error instanceof Error ? error.message : "IAM API unavailable");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [load]);

  const refresh = async () => {
    setRefreshing(true);
    try {
      await load(search);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Refresh failed");
    } finally {
      setRefreshing(false);
    }
  };

  const refreshSettings = async () => {
    setSettingsRefreshing(true);
    try {
      await load(search);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Settings refresh failed");
    } finally {
      setSettingsRefreshing(false);
    }
  };

  const openEdit = (user: IamUser) => {
    setEditUser(user);
    setEditForm({
      firstName: user.firstName ?? "",
      lastName: user.lastName ?? "",
      enabled: user.enabled,
      roles: [...user.roles],
      password: "",
    });
  };

  const submitInvite = async () => {
    setSaving(true);
    try {
      const created = await createIamUser({
        email: inviteForm.email.trim(),
        firstName: inviteForm.firstName.trim(),
        lastName: inviteForm.lastName.trim(),
        password: inviteForm.password,
        roles: inviteForm.roles,
      });
      toast.success(`Invited ${created.email ?? created.username}`);
      setInviteOpen(false);
      setInviteForm({
        email: "",
        firstName: "",
        lastName: "",
        password: "",
        roles: ["viewer"],
      });
      await load(search);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not create user");
    } finally {
      setSaving(false);
    }
  };

  const submitEdit = async () => {
    if (!editUser) return;
    setSaving(true);
    try {
      await updateIamUser(editUser.id, {
        firstName: editForm.firstName.trim(),
        lastName: editForm.lastName.trim(),
        enabled: editForm.enabled,
        roles: editForm.roles,
        password: editForm.password.trim() || undefined,
      });
      toast.success(`Updated ${displayName(editUser)}`);
      setEditUser(null);
      await load(search);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not update user");
    } finally {
      setSaving(false);
    }
  };

  const appRoles = catalog?.appRoles ?? ["platform_admin", "admin", "operator", "viewer"];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-on-surface-variant">
        <LoaderCircle className="h-6 w-6 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Tabs defaultValue="team" className="space-y-6">
        <TabsList className="flex h-auto flex-wrap justify-start gap-1 p-1">
          <TabsTrigger value="team" className="gap-2">
            <Users className="h-4 w-4" />
            Team members
          </TabsTrigger>
          <TabsTrigger value="access" className="gap-2">
            <ShieldCheck className="h-4 w-4" />
            Access policy
          </TabsTrigger>
          <TabsTrigger value="settings" className="gap-2">
            <SlidersHorizontal className="h-4 w-4" />
            Settings
          </TabsTrigger>
        </TabsList>

        <TabsContent value="team" className="space-y-6">
          <section className="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
        <div className="panel-elevated rounded-xl p-6 space-y-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-on-surface-variant">
                Your access
              </p>
              <h2 className="mt-2 font-display text-xl font-semibold">
                {me?.email ?? me?.subject ?? "Signed in"}
              </h2>
              <p className="text-sm text-on-surface-variant mt-1">
                Subject <span className="font-mono text-xs">{me?.subject}</span>
              </p>
            </div>
            <span className="size-11 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
              <Shield className="h-5 w-5" />
            </span>
          </div>
          <RoleBadges roles={me?.roles ?? []} />
          <p className="text-xs text-on-surface-variant">
            {me?.permissions.length ?? 0} effective permission
            {(me?.permissions.length ?? 0) === 1 ? "" : "s"}
            {me?.permissions.some((grant) => grant.resource === "*") ? " (full access)" : ""}
          </p>
        </div>

        <div className="panel-elevated rounded-xl p-6 space-y-3">
          <div className="flex items-center gap-2">
            <KeyRound className="h-4 w-4 text-on-surface-variant" />
            <h3 className="font-semibold text-sm">Identity provider</h3>
          </div>
          <p className="text-sm text-on-surface-variant leading-relaxed">
            {me?.oidcEnabled
              ? "Users and roles are stored in Keycloak. This console can list users and assign realm roles when you have admin access."
              : "OIDC is disabled in dev — the API uses a synthetic platform_admin principal."}
          </p>
          {me?.keycloakAdminUrl ? (
            <Button variant="outline" size="sm" asChild className="gap-2">
              <a href={me.keycloakAdminUrl} target="_blank" rel="noreferrer">
                Open Keycloak admin
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </Button>
          ) : null}
        </div>
      </section>

      <section className="panel-elevated rounded-xl overflow-hidden">
        <div className="px-6 py-5 border-b border-border bg-surface-container-low flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-on-surface-variant" />
              <h2 className="font-display text-lg font-semibold">Team members</h2>
            </div>
            <p className="text-sm text-on-surface-variant mt-1">
              Invite users and assign platform roles. Changes apply on next sign-in.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => void refresh()}
              disabled={refreshing}
              className="gap-2"
            >
              <RefreshCw className={cn("h-3.5 w-3.5", refreshing && "animate-spin")} />
              Refresh
            </Button>
            {me?.canManageUsers && usersState?.managementAvailable ? (
              <Button size="sm" className="gap-2" onClick={() => setInviteOpen(true)}>
                <Plus className="h-3.5 w-3.5" />
                Invite user
              </Button>
            ) : null}
          </div>
        </div>

        {usersState?.managementError ? (
          <div className="mx-6 mt-4 rounded-xl border border-warning/30 bg-warning-soft px-4 py-3 text-sm text-warning-strong">
            {usersState.managementError}
          </div>
        ) : null}

        <div className="px-6 py-4 border-b border-border/70">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface-variant" />
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") void load(search);
              }}
              placeholder="Search by name or email…"
              className="pl-9 h-9"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead>
              <tr className="border-b border-border bg-surface-container-lowest/60">
                <th className="px-6 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">
                  User
                </th>
                <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">
                  Roles
                </th>
                <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">
                  Status
                </th>
                <th className="px-6 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {(usersState?.users ?? []).length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-12 text-center text-on-surface-variant">
                    No users to show.
                  </td>
                </tr>
              ) : (
                usersState?.users.map((user) => (
                  <tr key={user.id} className="border-b border-border/70 hover:bg-surface-bright/40">
                    <td className="px-6 py-4">
                      <p className="font-medium">{displayName(user)}</p>
                      <p className="text-xs text-on-surface-variant mt-0.5">{user.email ?? user.username}</p>
                    </td>
                    <td className="px-4 py-4">
                      <RoleBadges roles={user.roles} />
                    </td>
                    <td className="px-4 py-4">
                      <Badge variant={user.enabled ? "success" : "outline"} className="text-[10px]">
                        {user.enabled ? "Active" : "Disabled"}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 text-right">
                      {me?.canManageUsers && usersState?.managementAvailable ? (
                        <Button variant="ghost" size="sm" className="gap-1.5" onClick={() => openEdit(user)}>
                          <UserCog className="h-3.5 w-3.5" />
                          Manage
                        </Button>
                      ) : (
                        <span className="text-xs text-on-surface-variant">—</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
        </TabsContent>

        <TabsContent value="access" className="space-y-6">
          <section className="grid gap-4 lg:grid-cols-3">
            <SettingMetric
              label="Current role"
              value={me?.roles[0] ?? "-"}
              detail={me?.email ?? me?.subject ?? "Signed in"}
              icon={Shield}
              tone="success"
            />
            <SettingMetric
              label="Permissions"
              value={`${me?.permissions.length ?? 0}`}
              detail={me?.permissions.some((grant) => grant.resource === "*") ? "Full access principal" : "Scoped access"}
              icon={Gauge}
            />
            <SettingMetric
              label="Policy roles"
              value={`${catalog?.appRoles.length ?? 0}`}
              detail="Keycloak realm roles mapped to backend RBAC"
              icon={Database}
            />
          </section>
          <PermissionMatrix catalog={catalog} />
        </TabsContent>

        <TabsContent value="settings">
          <SettingsPanel
            me={me}
            catalog={catalog}
            platform={platform}
            platformError={platformError}
            onRefresh={() => void refreshSettings()}
            refreshing={settingsRefreshing}
          />
        </TabsContent>
      </Tabs>

      <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Invite user</DialogTitle>
            <DialogDescription>
              Creates a Keycloak account with the selected platform roles.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="invite-email">Email</Label>
                <Input
                  id="invite-email"
                  type="email"
                  value={inviteForm.email}
                  onChange={(event) => setInviteForm((prev) => ({ ...prev, email: event.target.value }))}
                  placeholder="name@company.com"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="invite-first">First name</Label>
                <Input
                  id="invite-first"
                  value={inviteForm.firstName}
                  onChange={(event) => setInviteForm((prev) => ({ ...prev, firstName: event.target.value }))}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="invite-last">Last name</Label>
                <Input
                  id="invite-last"
                  value={inviteForm.lastName}
                  onChange={(event) => setInviteForm((prev) => ({ ...prev, lastName: event.target.value }))}
                />
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="invite-password">Temporary password</Label>
                <Input
                  id="invite-password"
                  type="password"
                  value={inviteForm.password}
                  onChange={(event) => setInviteForm((prev) => ({ ...prev, password: event.target.value }))}
                  placeholder="Minimum 8 characters"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Platform roles</Label>
              <RolePicker
                appRoles={appRoles}
                catalog={catalog}
                value={inviteForm.roles}
                onChange={(roles) => setInviteForm((prev) => ({ ...prev, roles }))}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setInviteOpen(false)} disabled={saving}>
              Cancel
            </Button>
            <Button
              onClick={() => void submitInvite()}
              disabled={saving || inviteForm.email.trim().length < 3 || inviteForm.password.length < 8}
            >
              {saving ? <LoaderCircle className="h-4 w-4 animate-spin" /> : "Create user"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!editUser} onOpenChange={(open) => !open && setEditUser(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Manage user</DialogTitle>
            <DialogDescription>
              {editUser ? displayName(editUser) : ""} — update roles, status, or password.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="edit-first">First name</Label>
                <Input
                  id="edit-first"
                  value={editForm.firstName}
                  onChange={(event) => setEditForm((prev) => ({ ...prev, firstName: event.target.value }))}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="edit-last">Last name</Label>
                <Input
                  id="edit-last"
                  value={editForm.lastName}
                  onChange={(event) => setEditForm((prev) => ({ ...prev, lastName: event.target.value }))}
                />
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="edit-password">New password (optional)</Label>
                <Input
                  id="edit-password"
                  type="password"
                  value={editForm.password}
                  onChange={(event) => setEditForm((prev) => ({ ...prev, password: event.target.value }))}
                  placeholder="Leave blank to keep current password"
                />
              </div>
            </div>
            <div className="flex items-center justify-between rounded-xl border border-border px-3 py-2.5">
              <div>
                <p className="text-sm font-medium">Account active</p>
                <p className="text-xs text-on-surface-variant">Disabled users cannot sign in.</p>
              </div>
              <Button
                type="button"
                size="sm"
                variant={editForm.enabled ? "default" : "outline"}
                onClick={() => setEditForm((prev) => ({ ...prev, enabled: !prev.enabled }))}
              >
                {editForm.enabled ? "Enabled" : "Disabled"}
              </Button>
            </div>
            <div className="space-y-2">
              <Label>Platform roles</Label>
              <RolePicker
                appRoles={appRoles}
                catalog={catalog}
                value={editForm.roles}
                onChange={(roles) => setEditForm((prev) => ({ ...prev, roles }))}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditUser(null)} disabled={saving}>
              Cancel
            </Button>
            <Button onClick={() => void submitEdit()} disabled={saving}>
              {saving ? <LoaderCircle className="h-4 w-4 animate-spin" /> : "Save changes"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
