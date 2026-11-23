"use client";

import { toast } from "@ui-sdk/react/toast";
import { Plus } from "lucide-react";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { useState } from "react";
import { NewClientDialog, useRefreshAdmin } from "@/components/admin/admin-dialogs";
import { RequestsSection } from "@/components/admin/requests-section";
import { Section } from "@/components/layout/page";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { $api } from "@/lib/api/browser";
import { errorMessage } from "@/lib/query/get-query-client";
import type { AdminEvent, AdminOverview, ClientSummary, SharedWorkflow } from "@/lib/types";
import { cn } from "@/lib/utils";

const SHARED = "__shared__";
// next-intl keys cannot hold dots: "user.invited" is the message "user_invited".
type ActionKey = {
  [A in AdminEvent["action"]]: A extends `${infer S}.${infer V}` ? `${S}_${V}` : A;
}[AdminEvent["action"]];
const th = "h-8 px-3 text-start text-xs font-medium text-ink-3";
const td = "h-9 px-3 text-[13px] tabular-nums";

export function AdminArea() {
  const t = useTranslations("admin");
  const overview = $api.useQuery("get", "/v1/admin");
  const [creating, setCreating] = useState(false);
  if (!overview.data) return <Skeleton.Lines count={8} />;
  const data = overview.data;
  return (
    <div className="flex flex-col gap-10">
      {data.enabled ? null : (
        <p className="rounded-md bg-warn-wash px-3 py-2 text-[13px] text-warn-ink">
          {t("notConfigured")}
        </p>
      )}
      <RequestsSection />
      <SpendSection data={data} />
      <Section
        title={t("clients")}
        hint={t("clientsHint", { threshold: data.lowBalanceThreshold })}
        actions={
          <Button
            variant="primary"
            size="sm"
            disabled={!data.enabled}
            onClick={() => setCreating(true)}
          >
            <Plus aria-hidden />
            {t("newClient")}
          </Button>
        }
      >
        <ClientsTable clients={data.clients} />
      </Section>
      <WorkflowsSection clients={data.clients} />
      <EventsSection />
      <NewClientDialog open={creating} onOpenChange={setCreating} />
    </div>
  );
}

function SpendSection({ data }: { data: AdminOverview }) {
  const t = useTranslations("admin");
  const format = useFormatter();
  const { spend } = data;
  const stats = [
    [t("spendDollars"), format.number(spend.dollars, { style: "currency", currency: "USD" })],
    [t("spendRuns"), format.number(spend.runs)],
    [t("spendPages"), format.number(spend.pages)],
    [t("spendModel"), format.number(spend.modelMs / 60000, { maximumFractionDigits: 1 })],
  ] as const;
  return (
    <Section
      title={t("spend")}
      hint={t("spendHint", {
        since: format.dateTime(new Date(spend.since), { dateStyle: "medium" }),
        rate: spend.dollarsPerHour,
      })}
    >
      <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-lg bg-line shadow-panel sm:grid-cols-4">
        {stats.map(([label, value]) => (
          <div key={label} className="bg-panel px-4 py-3">
            <dt className="text-xs text-ink-3">{label}</dt>
            <dd className="mt-1 text-[22px] font-semibold tracking-[-0.02em] tabular-nums text-ink">
              {value}
            </dd>
          </div>
        ))}
      </dl>
    </Section>
  );
}

function ClientsTable({ clients }: { clients: ClientSummary[] }) {
  const t = useTranslations("admin");
  const format = useFormatter();
  if (!clients.length)
    return (
      <p className="rounded-xl border border-dashed border-line-strong px-5 py-8 text-center text-[13px] text-ink-3">
        {t("noClients")}
      </p>
    );
  return (
    <div className="overflow-x-auto rounded-lg shadow-panel">
      <table className="w-full border-collapse">
        <thead className="border-b border-line bg-raised">
          <tr>
            <th className={th}>{t("client")}</th>
            <th className={th}>{t("users")}</th>
            <th className={cn(th, "text-end")}>{t("balance")}</th>
            <th className={cn(th, "text-end")}>{t("recentRuns")}</th>
            <th className={cn(th, "text-end")}>{t("recentPages")}</th>
            <th className={cn(th, "text-end")}>{t("workflows")}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {clients.map((client) => (
            <tr key={client.account} className="hover:bg-hover">
              <td className={td}>
                <Link
                  href={`/admin/clients/${client.account}`}
                  className="font-medium text-ink hover:underline"
                >
                  {client.account}
                </Link>
                {client.inKeycloak ? null : (
                  <span className="ms-2 text-xs text-warn-ink">{t("noGroup")}</span>
                )}
              </td>
              <td className={cn(td, "text-ink-2")}>
                {t("activeOf", { active: client.activeUsers, total: client.users })}
              </td>
              <td className={cn(td, "text-end")}>
                <span className="inline-flex items-center gap-1.5">
                  {client.lowBalance ? <StatusGlyph status="warning" className="size-3.5" /> : null}
                  {format.number(client.balance)}
                  {client.held ? (
                    <span className="text-xs text-ink-3">
                      {t("heldShort", { held: client.held })}
                    </span>
                  ) : null}
                </span>
              </td>
              <td className={cn(td, "text-end text-ink-2")}>{format.number(client.recentRuns)}</td>
              <td className={cn(td, "text-end text-ink-2")}>{format.number(client.recentPages)}</td>
              <td className={cn(td, "text-end text-ink-2")}>{client.workflows}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function WorkflowsSection({ clients }: { clients: ClientSummary[] }) {
  const t = useTranslations("admin");
  const workflows = $api.useQuery("get", "/v1/admin/workflows");
  return (
    <Section title={t("workflowsTitle")} hint={t("workflowsHint")}>
      {workflows.data ? (
        workflows.data.length ? (
          <ul className="divide-y divide-line rounded-lg shadow-panel">
            {workflows.data.map((wf) => (
              <WorkflowRow key={wf.id} workflow={wf} clients={clients} />
            ))}
          </ul>
        ) : (
          <p className="rounded-xl border border-dashed border-line-strong px-5 py-8 text-center text-[13px] text-ink-3">
            {t("noWorkflows")}
          </p>
        )
      ) : (
        <Skeleton.Lines count={3} />
      )}
    </Section>
  );
}

function WorkflowRow({
  workflow,
  clients,
}: {
  workflow: SharedWorkflow;
  clients: ClientSummary[];
}) {
  const t = useTranslations("admin");
  const refresh = useRefreshAdmin();
  const assign = $api.useMutation("put", "/v1/admin/workflows/{workflow_id}/account", {
    onSuccess: (wf) => {
      toast.success(
        wf.account ? t("assigned", { name: wf.name, account: wf.account }) : t("unassigned")
      );
      void refresh();
    },
    onError: (e) => toast.error(errorMessage(e, t("failed"))),
  });
  return (
    <li className="flex h-10 items-center gap-3 px-3">
      <Link
        href={`/workflows/${workflow.id}`}
        className="min-w-0 flex-1 truncate text-[13px] text-ink hover:underline"
      >
        {workflow.name || workflow.id}
      </Link>
      <Select
        value={workflow.account ?? SHARED}
        disabled={assign.isPending}
        onValueChange={(next: string | null) =>
          next &&
          assign.mutate({
            params: { path: { workflow_id: workflow.id } },
            body: { account: next === SHARED ? null : next },
          })
        }
      >
        <SelectTrigger aria-label={t("assignTo", { name: workflow.name })} className="w-48">
          {null}
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={SHARED}>{t("shared")}</SelectItem>
          {clients
            .filter((c) => c.inKeycloak)
            .map((c) => (
              <SelectItem key={c.account} value={c.account}>
                {c.account}
              </SelectItem>
            ))}
        </SelectContent>
      </Select>
    </li>
  );
}

export function EventsSection({ account }: { account?: string }) {
  const t = useTranslations("admin");
  const events = $api.useQuery("get", "/v1/admin/events", {
    params: { query: { account, limit: 50 } },
  });
  return (
    <Section title={t("auditLog")} hint={t("auditLogHint")}>
      {events.data ? (
        events.data.length ? (
          <ul className="divide-y divide-line rounded-lg shadow-panel">
            {events.data.map((event) => (
              <EventRow key={event.id} event={event} />
            ))}
          </ul>
        ) : (
          <p className="rounded-xl border border-dashed border-line-strong px-5 py-8 text-center text-[13px] text-ink-3">
            {t("noEvents")}
          </p>
        )
      ) : (
        <Skeleton.Lines count={4} />
      )}
    </Section>
  );
}

function EventRow({ event }: { event: AdminEvent }) {
  const t = useTranslations("admin");
  const format = useFormatter();
  const detail = event.detail as Record<string, unknown>;
  return (
    <li className="flex min-h-9 flex-wrap items-center gap-x-3 gap-y-0.5 px-3 py-1.5 text-[13px]">
      <span className="text-ink">
        {t(`actions.${event.action.replace(".", "_") as ActionKey}`)}
      </span>
      {event.account ? <span className="font-mono text-xs text-ink-2">{event.account}</span> : null}
      {event.target ? <span className="text-ink-2">{event.target}</span> : null}
      {typeof detail.amount === "number" ? (
        <span className="tabular-nums text-ink-2">
          {detail.amount > 0 ? "+" : ""}
          {format.number(detail.amount)}
        </span>
      ) : null}
      {typeof detail.role === "string" ? (
        <span className="text-ink-2">{t(`roles.${detail.role as "viewer"}`)}</span>
      ) : null}
      <span className="ms-auto text-xs text-ink-3 tabular-nums">
        {format.dateTime(new Date(event.createdAt), { dateStyle: "medium", timeStyle: "short" })}
      </span>
    </li>
  );
}
