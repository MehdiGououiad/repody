"use client";

import {
  ExternalLink,
  KeyRound,
  Plus,
  RefreshCw,
  Search,
  Shield,
  UserCog,
  Users,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { IamMe, IamUser } from "@/lib/api/iam";
import { cn } from "@/lib/utils";
import { displayName, RoleBadges } from "./user-access-shared";

export type UsersState = {
  users: IamUser[];
  managementAvailable: boolean;
  managementError?: string | null;
};

export function TeamPanel({
  me,
  usersState,
  search,
  refreshing,
  onSearchChange,
  onSearchSubmit,
  onRefresh,
  onInvite,
  onEdit,
}: {
  me: IamMe | null;
  usersState: UsersState | null;
  search: string;
  refreshing: boolean;
  onSearchChange: (value: string) => void;
  onSearchSubmit: () => void;
  onRefresh: () => void;
  onInvite: () => void;
  onEdit: (user: IamUser) => void;
}) {
  const canManageUsers = Boolean(me?.canManageUsers && usersState?.managementAvailable);

  return (
    <>
      <section className="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
        <div className="panel-elevated space-y-4 rounded-xl p-6">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-on-surface-variant">
                Your access
              </p>
              <h2 className="mt-2 font-display text-xl font-semibold">
                {me?.email ?? me?.subject ?? "Signed in"}
              </h2>
              <p className="mt-1 text-sm text-on-surface-variant">
                Subject <span className="font-mono text-xs">{me?.subject}</span>
              </p>
            </div>
            <span className="flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
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

        <div className="panel-elevated space-y-3 rounded-xl p-6">
          <div className="flex items-center gap-2">
            <KeyRound className="h-4 w-4 text-on-surface-variant" />
            <h3 className="text-sm font-semibold">Identity provider</h3>
          </div>
          <p className="text-sm leading-relaxed text-on-surface-variant">
            {me?.oidcEnabled
              ? "Users and roles are stored in Keycloak. This console can list users and assign realm roles when you have admin access."
              : "OIDC is disabled in dev - the API uses a synthetic platform_admin principal."}
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

      <section className="panel-elevated overflow-hidden rounded-xl">
        <div className="flex flex-col gap-4 border-b border-border bg-surface-container-low px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-on-surface-variant" />
              <h2 className="font-display text-lg font-semibold">Team members</h2>
            </div>
            <p className="mt-1 text-sm text-on-surface-variant">
              Invite users and assign platform roles. Changes apply on next sign-in.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" size="sm" onClick={onRefresh} disabled={refreshing} className="gap-2">
              <RefreshCw className={cn("h-3.5 w-3.5", refreshing && "animate-spin")} />
              Refresh
            </Button>
            {canManageUsers ? (
              <Button size="sm" className="gap-2" onClick={onInvite}>
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

        <div className="border-b border-border/70 px-6 py-4">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface-variant" />
            <Input
              value={search}
              onChange={(event) => onSearchChange(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") onSearchSubmit();
              }}
              placeholder="Search by name or email..."
              className="h-9 pl-9"
            />
          </div>
        </div>

        <TeamMembersTable
          users={usersState?.users ?? []}
          canManageUsers={canManageUsers}
          onEdit={onEdit}
        />
      </section>
    </>
  );
}

function TeamMembersTable({
  users,
  canManageUsers,
  onEdit,
}: {
  users: IamUser[];
  canManageUsers: boolean;
  onEdit: (user: IamUser) => void;
}) {
  return (
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
          {users.length === 0 ? (
            <tr>
              <td colSpan={4} className="px-6 py-12 text-center text-on-surface-variant">
                No users to show.
              </td>
            </tr>
          ) : (
            users.map((user) => (
              <tr key={user.id} className="border-b border-border/70 hover:bg-surface-bright/40">
                <td className="px-6 py-4">
                  <p className="font-medium">{displayName(user)}</p>
                  <p className="mt-0.5 text-xs text-on-surface-variant">{user.email ?? user.username}</p>
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
                  {canManageUsers ? (
                    <Button variant="ghost" size="sm" className="gap-1.5" onClick={() => onEdit(user)}>
                      <UserCog className="h-3.5 w-3.5" />
                      Manage
                    </Button>
                  ) : (
                    <span className="text-xs text-on-surface-variant">-</span>
                  )}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
