"use client";

import { useMemo } from "react";
import { ShieldCheck } from "lucide-react";
import type { IamCatalog } from "@/lib/api/iam";

export function PermissionMatrix({ catalog }: { catalog: IamCatalog | null }) {
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
    return <div className="panel-elevated h-40 animate-pulse rounded-xl" />;
  }

  return (
    <section className="panel-elevated overflow-hidden rounded-xl">
      <div className="border-b border-border bg-surface-container-low px-6 py-5">
        <h2 className="font-display text-lg font-semibold">Role permissions</h2>
        <p className="mt-1 text-sm text-on-surface-variant">
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
                      <span className="text-on-surface-variant/30">-</span>
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
