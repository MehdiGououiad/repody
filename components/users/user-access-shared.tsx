"use client";

import { ShieldCheck, type LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { IamCatalog, IamUser } from "@/lib/api/iam";

export const ROLE_BADGE: Record<string, "default" | "secondary" | "info" | "outline"> = {
  platform_admin: "default",
  admin: "default",
  operator: "info",
  viewer: "secondary",
};

export function displayName(user: IamUser) {
  const full = [user.firstName, user.lastName].filter(Boolean).join(" ").trim();
  return full || user.email || user.username;
}

export function RoleBadges({ roles }: { roles: string[] }) {
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

export function RolePicker({
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

export function SettingMetric({
  label,
  value,
  detail,
  icon: Icon,
  tone = "info",
}: {
  label: string;
  value: string;
  detail: string;
  icon: LucideIcon;
  tone?: "info" | "success" | "warning";
}) {
  const toneClass = {
    info: "bg-info-soft text-info",
    success: "bg-success-soft text-success-strong",
    warning: "bg-warning-soft text-warning-strong",
  }[tone];

  return (
    <div className="panel-elevated min-w-0 rounded-xl p-5">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-on-surface-variant">
          {label}
        </p>
        <span className={cn("flex size-9 items-center justify-center rounded-lg", toneClass)}>
          <Icon className="h-4 w-4" aria-hidden="true" />
        </span>
      </div>
      <p className="mt-4 truncate font-display text-2xl font-semibold text-on-surface">{value}</p>
      <p className="mt-1 text-xs text-on-surface-variant">{detail}</p>
    </div>
  );
}

export function StatusLine({
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

export function ConfigTable({
  title,
  description,
  rows,
}: {
  title: string;
  description: string;
  rows: Array<[string, string]>;
}) {
  return (
    <section className="panel-elevated overflow-hidden rounded-xl">
      <div className="border-b border-border bg-surface-container-low px-6 py-5">
        <h3 className="font-display text-lg font-semibold">{title}</h3>
        <p className="mt-1 text-sm text-on-surface-variant">{description}</p>
      </div>
      <dl className="grid sm:grid-cols-2">
        {rows.map(([label, value]) => (
          <div key={label} className="min-w-0 border-b border-r border-border/70 px-5 py-4">
            <dt className="text-[11px] uppercase tracking-wider text-on-surface-variant">{label}</dt>
            <dd className="mt-1 break-words font-mono text-sm text-on-surface">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
