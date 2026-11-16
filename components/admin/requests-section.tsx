"use client";

import { Field, FieldDescription, FieldError, FieldLabel } from "@ui-sdk/react/field";
import { toast } from "@ui-sdk/react/toast";
import { useFormatter, useTranslations } from "next-intl";
import { useState } from "react";
import { PasswordDialog, RoleSelect, useRefreshAdmin } from "@/components/admin/admin-dialogs";
import { Section } from "@/components/layout/page";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogBackdrop,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { confirmAction } from "@/components/ui/overlays";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { $api } from "@/lib/api/browser";
import { errorMessage } from "@/lib/query/get-query-client";
import type { AccessRequest, ClientRole, TemporaryPassword } from "@/lib/types";

const SLUG_LENGTH = 50;

/** A client name from a company: lowercase ASCII letters and digits, runs of anything else as one
 * dash, none at the ends (the admin can change it). A loop, not regexes that could backtrack. */
export function slugOf(company: string): string {
  const letters = company.normalize("NFKD").toLowerCase();
  let slug = "";
  for (const char of letters) {
    if ((char >= "a" && char <= "z") || (char >= "0" && char <= "9")) slug += char;
    else if (char.charCodeAt(0) < 0x300 || char.charCodeAt(0) > 0x36f) {
      if (slug && !slug.endsWith("-")) slug += "-";
    }
  }
  slug = slug.slice(0, SLUG_LENGTH);
  while (slug.endsWith("-")) slug = slug.slice(0, -1);
  return slug;
}

function formText(form: FormData, name: string, fallback = ""): string {
  const value = form.get(name);
  return typeof value === "string" ? value : fallback;
}

const GLYPH = { new: "waiting", approved: "passed", declined: "skipped" } as const;

export function RequestsSection() {
  const t = useTranslations("admin");
  const requests = $api.useQuery("get", "/v1/admin/requests");
  const [approving, setApproving] = useState<AccessRequest | null>(null);
  const [password, setPassword] = useState<TemporaryPassword | null>(null);
  const waiting = (requests.data ?? []).filter((r) => r.status === "new");
  return (
    <Section title={t("requests")} count={waiting.length} hint={t("requestsHint")}>
      <RequestList items={requests.data} empty={t("noRequests")} onApprove={setApproving} />
      <ApproveDialog
        request={approving}
        onClose={() => setApproving(null)}
        onApproved={setPassword}
      />
      <PasswordDialog result={password} onClose={() => setPassword(null)} />
    </Section>
  );
}

function RequestList({
  items,
  empty,
  onApprove,
}: Readonly<{
  items: AccessRequest[] | undefined;
  empty: string;
  onApprove: (request: AccessRequest) => void;
}>) {
  if (!items) return <Skeleton.Lines count={3} />;
  if (!items.length) return <p className="py-6 text-[13px] text-ink-3">{empty}</p>;
  return (
    <ul className="divide-y divide-line rounded-lg shadow-[0_0_0_1px_var(--line)]">
      {items.slice(0, 30).map((request) => (
        <RequestRow key={request.id} request={request} onApprove={onApprove} />
      ))}
    </ul>
  );
}

function RequestRow({
  request,
  onApprove,
}: Readonly<{
  request: AccessRequest;
  onApprove: (request: AccessRequest) => void;
}>) {
  const t = useTranslations("admin");
  const tCommon = useTranslations("common");
  const format = useFormatter();
  const refresh = useRefreshAdmin();
  const decline = $api.useMutation("post", "/v1/admin/requests/{request_id}/decline", {
    onSuccess: () => {
      toast.success(t("declined"));
      void refresh();
    },
    onError: (e) => toast.error(errorMessage(e, t("failed"))),
  });
  const glyph = GLYPH[request.status];
  return (
    <li className="flex flex-col gap-1 px-3 py-2.5 text-[13px]">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <StatusGlyph
          status={glyph}
          className="size-3.5"
          label={t(`requestStatus.${request.status}`)}
        />
        <span className="font-medium text-ink">{request.company}</span>
        <span className="text-ink-2">
          {request.name} · {request.email}
        </span>
        {request.sector ? <span className="text-xs text-ink-3">{request.sector}</span> : null}
        <span className="ms-auto text-xs text-ink-3 tabular-nums">
          {format.dateTime(new Date(request.createdAt), {
            dateStyle: "medium",
            timeStyle: "short",
          })}
        </span>
      </div>
      {request.message ? <p className="whitespace-pre-line text-ink-2">{request.message}</p> : null}
      {request.status === "new" ? (
        <div className="flex gap-2 pt-1">
          <Button
            size="xs"
            variant="primary"
            aria-label={t("approveFor", { company: request.company })}
            onClick={() => onApprove(request)}
          >
            {t("approve")}
          </Button>
          <Button
            size="xs"
            variant="ghost"
            aria-label={t("declineFor", { company: request.company })}
            disabled={decline.isPending}
            onClick={async () => {
              const yes = await confirmAction({
                title: t("declineTitle", { company: request.company }),
                description: t("declineHint"),
                confirmLabel: t("declineConfirm"),
                cancelLabel: tCommon("cancel"),
                danger: true,
              });
              if (yes)
                decline.mutate({
                  params: { path: { request_id: request.id } },
                  body: { note: "" },
                });
            }}
          >
            {t("decline")}
          </Button>
        </div>
      ) : (
        <p className="text-xs text-ink-3">
          {request.status === "approved"
            ? t("approvedInto", { account: request.account ?? "" })
            : t("declinedNote", { note: request.note || "—" })}
        </p>
      )}
    </li>
  );
}

function ApproveDialog({
  request,
  onClose,
  onApproved,
}: Readonly<{
  request: AccessRequest | null;
  onClose: () => void;
  onApproved: (invited: TemporaryPassword) => void;
}>) {
  const t = useTranslations("admin");
  const tCommon = useTranslations("common");
  const refresh = useRefreshAdmin();
  const [error, setError] = useState<string | null>(null);
  const approve = $api.useMutation("post", "/v1/admin/requests/{request_id}/approve", {
    onSuccess: (result) => {
      void refresh();
      onClose();
      onApproved(result.invited);
    },
    onError: (e) => setError(errorMessage(e, t("failed"))),
  });
  return (
    <Dialog
      open={request !== null}
      onOpenChange={(open) => {
        if (!open) {
          setError(null);
          onClose();
        }
      }}
    >
      <DialogBackdrop />
      <DialogContent size="sm">
        {request ? (
          <form
            key={request.id}
            onSubmit={(event) => {
              event.preventDefault();
              const form = new FormData(event.currentTarget);
              setError(null);
              approve.mutate({
                params: { path: { request_id: request.id } },
                body: {
                  slug: formText(form, "slug"),
                  role: formText(form, "role", "admin") as ClientRole,
                  credits: Number(formText(form, "credits", "200")),
                },
              });
            }}
          >
            <DialogHeader>
              <DialogTitle>{t("approveTitle", { company: request.company })}</DialogTitle>
              <DialogDescription>{t("approveHint", { email: request.email })}</DialogDescription>
            </DialogHeader>
            <DialogBody className="flex flex-col gap-3">
              <Field name="slug" invalid={error !== null}>
                <FieldLabel className="text-xs text-ink-2">{t("clientSlug")}</FieldLabel>
                <div className="mt-1 flex items-center gap-1 font-mono text-xs text-ink-3">
                  client-
                  <Input
                    required
                    defaultValue={slugOf(request.company)}
                    pattern="[a-z0-9]([a-z0-9\-]{0,48}[a-z0-9])?"
                    autoComplete="off"
                    spellCheck={false}
                    className="font-mono"
                  />
                </div>
                <FieldDescription className="mt-1 text-xs text-ink-3">
                  {t("approveSlugHint")}
                </FieldDescription>
                {error ? (
                  <FieldError match className="mt-1 text-xs text-fail-ink">
                    {error}
                  </FieldError>
                ) : null}
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field>
                  <FieldLabel className="text-xs text-ink-2">{t("role")}</FieldLabel>
                  <div className="mt-1">
                    <RoleSelect name="role" label={t("role")} initial="admin" />
                  </div>
                </Field>
                <Field name="credits">
                  <FieldLabel className="text-xs text-ink-2">{t("startingCredits")}</FieldLabel>
                  <Input
                    type="number"
                    inputMode="numeric"
                    min={0}
                    max={100000}
                    step={10}
                    defaultValue="200"
                    required
                    className="mt-1 tabular-nums"
                  />
                </Field>
              </div>
            </DialogBody>
            <DialogFooter>
              <Button type="button" variant="ghost" onClick={onClose}>
                {tCommon("cancel")}
              </Button>
              <Button
                type="submit"
                variant="primary"
                disabled={approve.isPending}
                data-agent-confirm={t("approveConfirm", { company: request.company })}
              >
                {t("approveSubmit")}
              </Button>
            </DialogFooter>
          </form>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
