"use client";

import { toast } from "@ui-sdk/react/toast";
import { Coins, MoreHorizontal, UserPlus } from "lucide-react";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { useState } from "react";
import { EventsSection } from "@/components/admin/admin-area";
import {
  GrantDialog,
  InviteUserDialog,
  PasswordDialog,
  RoleSelect,
  useRefreshAdmin,
} from "@/components/admin/admin-dialogs";
import { Crumb, Page, Section } from "@/components/layout/page";
import { Button } from "@/components/ui/button";
import { Menu, MenuContent, MenuItem, MenuSeparator, MenuTrigger } from "@/components/ui/menu";
import { confirmAction } from "@/components/ui/overlays";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { $api } from "@/lib/api/browser";
import { errorMessage } from "@/lib/query/get-query-client";
import type { ClientDetail, ClientUser, LedgerEntry, TemporaryPassword } from "@/lib/types";
import { cn } from "@/lib/utils";

const th = "h-8 px-3 text-start text-xs font-medium text-ink-3";
const td = "h-9 px-3 text-[13px]";

export function ClientPage({ account }: { account: string }) {
  const t = useTranslations("admin");
  const detail = $api.useQuery("get", "/v1/admin/clients/{account}", {
    params: { path: { account } },
  });
  const [inviting, setInviting] = useState(false);
  const [granting, setGranting] = useState(false);
  const [password, setPassword] = useState<TemporaryPassword | null>(null);
  const data = detail.data;
  return (
    <Page
      trail={<Crumb href="/admin">{t("title")}</Crumb>}
      title={account}
      actions={
        data ? (
          <>
            <Button size="sm" onClick={() => setGranting(true)}>
              <Coins aria-hidden />
              {t("grantCredits")}
            </Button>
            <Button
              size="sm"
              variant="primary"
              disabled={!data.summary.inKeycloak}
              onClick={() => setInviting(true)}
            >
              <UserPlus aria-hidden />
              {t("inviteUser")}
            </Button>
            <ClientMenu account={account} data={data} />
          </>
        ) : null
      }
    >
      {data ? (
        <div className="flex flex-col gap-8">
          <Balance data={data} />
          <Section title={t("users")} count={data.users.length}>
            <UsersTable account={account} users={data.users} onPassword={setPassword} />
          </Section>
          <Section title={t("ledger")} hint={t("ledgerHint")}>
            <Ledger entries={data.ledger} />
          </Section>
          <Section title={t("workflows")} count={data.workflows.length}>
            {data.workflows.length ? (
              <ul className="divide-y divide-line rounded-lg shadow-[0_0_0_1px_var(--line)]">
                {data.workflows.map((wf) => (
                  <li key={wf.id} className="flex h-9 items-center px-3 text-[13px]">
                    <Link href={`/workflows/${wf.id}`} className="text-ink hover:underline">
                      {wf.name || wf.id}
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-[13px] text-ink-3">{t("noClientWorkflows")}</p>
            )}
          </Section>
          <EventsSection account={account} />
        </div>
      ) : detail.error ? (
        <p className="text-[13px] text-fail-ink">{errorMessage(detail.error, t("failed"))}</p>
      ) : (
        <Skeleton.Lines count={8} />
      )}
      <InviteUserDialog
        account={account}
        open={inviting}
        onOpenChange={setInviting}
        onInvited={setPassword}
      />
      <GrantDialog account={account} open={granting} onOpenChange={setGranting} />
      <PasswordDialog result={password} onClose={() => setPassword(null)} />
    </Page>
  );
}

function Balance({ data }: { data: ClientDetail }) {
  const t = useTranslations("admin");
  const format = useFormatter();
  const { summary } = data;
  return (
    <div className="flex flex-wrap items-end gap-x-8 gap-y-2">
      <div>
        <p className="text-xs text-ink-3">{t("balance")}</p>
        <p className="flex items-center gap-2 text-[22px] font-semibold tracking-[-0.02em] tabular-nums text-ink">
          {summary.lowBalance ? <StatusGlyph status="warning" className="size-4" /> : null}
          {format.number(summary.balance)}
        </p>
      </div>
      <p className="text-[13px] text-ink-2 tabular-nums">
        {t("detailStats", {
          held: summary.held,
          runs: summary.recentRuns,
          pages: summary.recentPages,
        })}
      </p>
    </div>
  );
}

function ClientMenu({ account, data }: { account: string; data: ClientDetail }) {
  const t = useTranslations("admin");
  const tCommon = useTranslations("common");
  const refresh = useRefreshAdmin();
  const onError = (e: unknown) => toast.error(errorMessage(e, t("failed")));
  const disable = $api.useMutation("post", "/v1/admin/clients/{account}/disable", {
    onSuccess: () => {
      toast.success(t("clientDisabled"));
      void refresh();
    },
    onError,
  });
  const enable = $api.useMutation("post", "/v1/admin/clients/{account}/enable", {
    onSuccess: () => {
      toast.success(t("clientEnabled"));
      void refresh();
    },
    onError,
  });
  const path = { params: { path: { account } } };
  return (
    <Menu>
      <MenuTrigger
        render={<Button size="icon-sm" variant="ghost" aria-label={t("clientActions")} />}
      >
        <MoreHorizontal aria-hidden />
      </MenuTrigger>
      <MenuContent>
        <MenuItem disabled={!data.summary.inKeycloak} onClick={() => enable.mutate(path)}>
          {t("enableAll")}
        </MenuItem>
        <MenuSeparator />
        <MenuItem
          danger
          disabled={!data.summary.inKeycloak}
          onClick={async () => {
            const yes = await confirmAction({
              title: t("disableTitle", { account }),
              description: t("disableHint"),
              confirmLabel: t("disableAll"),
              cancelLabel: tCommon("cancel"),
              danger: true,
            });
            if (yes) disable.mutate(path);
          }}
        >
          {t("disableAll")}
        </MenuItem>
      </MenuContent>
    </Menu>
  );
}

function UsersTable({
  account,
  users,
  onPassword,
}: {
  account: string;
  users: ClientUser[];
  onPassword: (result: TemporaryPassword) => void;
}) {
  const t = useTranslations("admin");
  if (!users.length) return <p className="text-[13px] text-ink-3">{t("noUsers")}</p>;
  return (
    <div className="overflow-x-auto rounded-lg shadow-[0_0_0_1px_var(--line)]">
      <table className="w-full border-collapse">
        <thead className="border-b border-line bg-raised">
          <tr>
            <th className={th}>{t("email")}</th>
            <th className={th}>{t("name")}</th>
            <th className={th}>{t("role")}</th>
            <th className={th}>{t("status")}</th>
            <th className={th}>
              <span className="sr-only">{t("userActions")}</span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {users.map((user) => (
            <UserRow key={user.id} account={account} user={user} onPassword={onPassword} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function UserRow({
  account,
  user,
  onPassword,
}: {
  account: string;
  user: ClientUser;
  onPassword: (result: TemporaryPassword) => void;
}) {
  const t = useTranslations("admin");
  const tCommon = useTranslations("common");
  const refresh = useRefreshAdmin();
  const onError = (e: unknown) => toast.error(errorMessage(e, t("failed")));
  const path = { params: { path: { account, user_id: user.id } } };
  const change = $api.useMutation("patch", "/v1/admin/clients/{account}/users/{user_id}", {
    onSuccess: () => void refresh(),
    onError,
  });
  const reset = $api.useMutation("post", "/v1/admin/clients/{account}/users/{user_id}/password", {
    onSuccess: onPassword,
    onError,
  });
  const remove = $api.useMutation("delete", "/v1/admin/clients/{account}/users/{user_id}", {
    onSuccess: () => {
      toast.success(t("userRemoved", { email: user.email }));
      void refresh();
    },
    onError,
  });
  const name = [user.firstName, user.lastName].filter(Boolean).join(" ");
  return (
    <tr className="hover:bg-hover">
      <td className={cn(td, "text-ink")}>{user.email}</td>
      <td className={cn(td, "text-ink-2")}>{name || "—"}</td>
      <td className={td}>
        <RoleSelect
          value={user.role ?? undefined}
          label={t("roleOf", { email: user.email })}
          disabled={change.isPending}
          onValueChange={(role) => change.mutate({ ...path, body: { role } })}
        />
      </td>
      <td className={td}>
        <span className="inline-flex items-center gap-1.5 text-ink-2">
          <StatusGlyph status={user.enabled ? "passed" : "skipped"} className="size-3.5" />
          {user.enabled ? t("active") : t("disabled")}
        </span>
      </td>
      <td className={cn(td, "text-end")}>
        <Menu>
          <MenuTrigger
            render={
              <Button
                size="icon-xs"
                variant="ghost"
                aria-label={t("actionsFor", { email: user.email })}
              />
            }
          >
            <MoreHorizontal aria-hidden />
          </MenuTrigger>
          <MenuContent>
            <MenuItem
              data-agent-confirm={t("resetConfirm", { email: user.email })}
              onClick={() => reset.mutate(path)}
            >
              {t("resetPassword")}
            </MenuItem>
            <MenuItem onClick={() => change.mutate({ ...path, body: { enabled: !user.enabled } })}>
              {user.enabled ? t("disable") : t("enable")}
            </MenuItem>
            <MenuSeparator />
            <MenuItem
              danger
              onClick={async () => {
                const yes = await confirmAction({
                  title: t("removeTitle", { email: user.email }),
                  description: t("removeHint", { account }),
                  confirmLabel: t("remove"),
                  cancelLabel: tCommon("cancel"),
                  danger: true,
                });
                if (yes) remove.mutate(path);
              }}
            >
              {t("remove")}
            </MenuItem>
          </MenuContent>
        </Menu>
      </td>
    </tr>
  );
}

function Ledger({ entries }: { entries: LedgerEntry[] }) {
  const t = useTranslations("admin");
  const format = useFormatter();
  if (!entries.length) return <p className="text-[13px] text-ink-3">{t("noLedger")}</p>;
  return (
    <div className="overflow-x-auto rounded-lg shadow-[0_0_0_1px_var(--line)]">
      <table className="w-full border-collapse">
        <thead className="border-b border-line bg-raised">
          <tr>
            <th className={th}>{t("when")}</th>
            <th className={th}>{t("entry")}</th>
            <th className={cn(th, "text-end")}>{t("credits")}</th>
            <th className={cn(th, "text-end")}>{t("pages")}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {entries.map((entry) => (
            <tr key={entry.id}>
              <td className={cn(td, "text-xs text-ink-3 tabular-nums")}>
                {format.dateTime(new Date(entry.createdAt), {
                  dateStyle: "medium",
                  timeStyle: "short",
                })}
              </td>
              <td className={cn(td, "text-ink-2")}>
                {entry.kind === "grant" ? (
                  <>
                    {t("grantEntry")}
                    {entry.note ? <span className="ms-2 text-ink-3">{entry.note}</span> : null}
                  </>
                ) : entry.runId ? (
                  <Link href={`/audits/${entry.runId}`} className="hover:underline">
                    {entry.pending ? t("runHeld") : t("runEntry")}
                  </Link>
                ) : (
                  t("runEntry")
                )}
              </td>
              <td
                className={`${td} text-end tabular-nums ${entry.amount < 0 ? "text-ink" : "text-pass-ink"}`}
              >
                {entry.amount > 0 ? "+" : ""}
                {format.number(entry.amount)}
              </td>
              <td className={cn(td, "text-end text-ink-3 tabular-nums")}>
                {entry.kind === "run" ? format.number(entry.pages) : ""}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
