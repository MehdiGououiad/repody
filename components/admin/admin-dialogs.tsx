"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Field, FieldDescription, FieldError, FieldLabel } from "@ui-sdk/react/field";
import {
  NumberInput,
  NumberInputControl,
  NumberInputDecrement,
  NumberInputGroup,
  NumberInputIncrement,
} from "@ui-sdk/react/number-input";
import { toast } from "@ui-sdk/react/toast";
import { Copy, Minus, Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
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
import { fieldClass, Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";
import { $api } from "@/lib/api/browser";
import { useCopyToClipboard } from "@/lib/hooks/use-copy-to-clipboard";
import { errorMessage } from "@/lib/query/get-query-client";
import type { ClientRole, TemporaryPassword } from "@/lib/types";
import { cn } from "@/lib/utils";

export const CLIENT_ROLES: ClientRole[] = ["viewer", "operator", "admin"];

export function useRefreshAdmin() {
  const queryClient = useQueryClient();
  return () =>
    queryClient.invalidateQueries({
      predicate: (query) => String(query.queryKey[1] ?? "").startsWith("/v1/admin"),
    });
}

type DialogProps = { open: boolean; onOpenChange: (open: boolean) => void };

export function NewClientDialog({ open, onOpenChange }: DialogProps) {
  const t = useTranslations("admin");
  const tCommon = useTranslations("common");
  const refresh = useRefreshAdmin();
  const [error, setError] = useState<string | null>(null);
  const create = $api.useMutation("post", "/v1/admin/clients", {
    onSuccess: (client) => {
      toast.success(t("clientCreated", { account: client.account }));
      void refresh();
      onOpenChange(false);
    },
    onError: (e) => setError(errorMessage(e, t("failed"))),
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogBackdrop />
      <DialogContent size="sm">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            const slug = String(new FormData(event.currentTarget).get("slug") ?? "").trim();
            setError(null);
            create.mutate({ body: { slug } });
          }}
        >
          <DialogHeader>
            <DialogTitle>{t("newClient")}</DialogTitle>
            <DialogDescription>{t("newClientHint")}</DialogDescription>
          </DialogHeader>
          <DialogBody>
            <Field name="slug" invalid={error !== null}>
              <FieldLabel className="text-xs text-ink-2">{t("clientSlug")}</FieldLabel>
              <div className="mt-1 flex items-center gap-1 font-mono text-xs text-ink-3">
                client-
                <Input
                  required
                  pattern="[a-z0-9]([a-z0-9\-]{0,48}[a-z0-9])?"
                  autoComplete="off"
                  spellCheck={false}
                  className="font-mono"
                  onChange={() => setError(null)}
                />
              </div>
              <FieldDescription className="mt-1 text-xs text-ink-3">
                {t("clientSlugHint")}
              </FieldDescription>
              <FieldError match="patternMismatch" className="mt-1 text-xs text-fail-ink">
                {t("clientSlugHint")}
              </FieldError>
              {error ? (
                <FieldError match className="mt-1 text-xs text-fail-ink">
                  {error}
                </FieldError>
              ) : null}
            </Field>
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              {tCommon("cancel")}
            </Button>
            <Button type="submit" variant="primary" disabled={create.isPending}>
              {t("create")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function RoleSelect({
  value,
  initial = "operator",
  onValueChange,
  label,
  name,
  disabled,
}: {
  value?: ClientRole;
  initial?: ClientRole;
  onValueChange?: (role: ClientRole) => void;
  label: string;
  name?: string;
  disabled?: boolean;
}) {
  const t = useTranslations("admin");
  return (
    <Select
      name={name}
      defaultValue={value === undefined ? initial : undefined}
      value={value}
      disabled={disabled}
      onValueChange={(next: string | null) => next && onValueChange?.(next as ClientRole)}
    >
      <SelectTrigger aria-label={label} className="w-32">
        {null}
      </SelectTrigger>
      <SelectContent>
        {CLIENT_ROLES.map((role) => (
          <SelectItem key={role} value={role}>
            {t(`roles.${role}`)}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export function InviteUserDialog({
  account,
  open,
  onOpenChange,
  onInvited,
}: DialogProps & { account: string; onInvited: (result: TemporaryPassword) => void }) {
  const t = useTranslations("admin");
  const tCommon = useTranslations("common");
  const refresh = useRefreshAdmin();
  const [error, setError] = useState<string | null>(null);
  const invite = $api.useMutation("post", "/v1/admin/clients/{account}/users", {
    onSuccess: (result) => {
      void refresh();
      onOpenChange(false);
      onInvited(result);
    },
    onError: (e) => setError(errorMessage(e, t("failed"))),
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogBackdrop />
      <DialogContent size="sm">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            setError(null);
            invite.mutate({
              params: { path: { account } },
              body: {
                email: String(form.get("email") ?? ""),
                firstName: String(form.get("firstName") ?? ""),
                lastName: String(form.get("lastName") ?? ""),
                role: String(form.get("role") ?? "operator") as ClientRole,
              },
            });
          }}
        >
          <DialogHeader>
            <DialogTitle>{t("inviteUser")}</DialogTitle>
            <DialogDescription>{t("inviteHint", { account })}</DialogDescription>
          </DialogHeader>
          <DialogBody className="flex flex-col gap-3">
            <Field name="email" invalid={error !== null}>
              <FieldLabel className="text-xs text-ink-2">{t("email")}</FieldLabel>
              <Input type="email" required autoComplete="off" className="mt-1" />
              <FieldError match="typeMismatch" className="mt-1 text-xs text-fail-ink">
                {t("emailInvalid")}
              </FieldError>
              {error ? (
                <FieldError match className="mt-1 text-xs text-fail-ink">
                  {error}
                </FieldError>
              ) : null}
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field name="firstName">
                <FieldLabel className="text-xs text-ink-2">{t("firstName")}</FieldLabel>
                <Input autoComplete="off" className="mt-1" />
              </Field>
              <Field name="lastName">
                <FieldLabel className="text-xs text-ink-2">{t("lastName")}</FieldLabel>
                <Input autoComplete="off" className="mt-1" />
              </Field>
            </div>
            <Field>
              <FieldLabel className="text-xs text-ink-2">{t("role")}</FieldLabel>
              <div className="mt-1">
                <RoleSelect name="role" label={t("role")} />
              </div>
              <FieldDescription className="mt-1 text-xs text-ink-3">
                {t("roleHint")}
              </FieldDescription>
            </Field>
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              {tCommon("cancel")}
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={invite.isPending}
              data-agent-confirm={t("inviteConfirm", { account })}
            >
              {t("invite")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function GrantDialog({ account, open, onOpenChange }: DialogProps & { account: string }) {
  const t = useTranslations("admin");
  const tCommon = useTranslations("common");
  const refresh = useRefreshAdmin();
  const [amount, setAmount] = useState<number | null>(200);
  const [error, setError] = useState<string | null>(null);
  const grant = $api.useMutation("post", "/v1/admin/clients/{account}/credits", {
    onSuccess: (credits) => {
      toast.success(t("granted", { account, balance: credits.balance }));
      void refresh();
      onOpenChange(false);
    },
    onError: (e) => setError(errorMessage(e, t("failed"))),
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogBackdrop />
      <DialogContent size="sm">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            if (!amount) return;
            const note = String(new FormData(event.currentTarget).get("note") ?? "");
            setError(null);
            grant.mutate({ params: { path: { account } }, body: { amount, note } });
          }}
        >
          <DialogHeader>
            <DialogTitle>{t("grantCredits")}</DialogTitle>
            <DialogDescription>{t("grantHint")}</DialogDescription>
          </DialogHeader>
          <DialogBody className="flex flex-col gap-3">
            <Field invalid={error !== null}>
              <FieldLabel className="text-xs text-ink-2">{t("credits")}</FieldLabel>
              <NumberInput
                value={amount}
                onValueChange={setAmount}
                min={-1_000_000}
                max={1_000_000}
                step={10}
                required
              >
                <NumberInputGroup className="mt-1 flex items-center gap-1">
                  <NumberInputDecrement
                    aria-label={t("less")}
                    className="grid size-8 place-items-center rounded-md text-ink-2 hover:bg-hover"
                  >
                    <Minus className="size-3.5" aria-hidden />
                  </NumberInputDecrement>
                  <NumberInputControl className={cn(fieldClass, "h-8 w-32 tabular-nums")} />
                  <NumberInputIncrement
                    aria-label={t("more")}
                    className="grid size-8 place-items-center rounded-md text-ink-2 hover:bg-hover"
                  >
                    <Plus className="size-3.5" aria-hidden />
                  </NumberInputIncrement>
                </NumberInputGroup>
              </NumberInput>
              <FieldDescription className="mt-1 text-xs text-ink-3">
                {t("creditsHint")}
              </FieldDescription>
              {error ? (
                <FieldError match className="mt-1 text-xs text-fail-ink">
                  {error}
                </FieldError>
              ) : null}
            </Field>
            <Field name="note">
              <FieldLabel className="text-xs text-ink-2">{t("note")}</FieldLabel>
              <Input autoComplete="off" className="mt-1" placeholder={t("notePlaceholder")} />
            </Field>
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              {tCommon("cancel")}
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={grant.isPending || !amount}
              data-agent-confirm={t("grantConfirm", { account, amount: amount ?? 0 })}
            >
              {amount !== null && amount < 0 ? t("takeBack") : t("grant")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/** The temporary password, shown once: Keycloak asks for a new one at the first sign-in. */
export function PasswordDialog({
  result,
  onClose,
}: {
  result: TemporaryPassword | null;
  onClose: () => void;
}) {
  const t = useTranslations("admin");
  const { copy } = useCopyToClipboard();
  return (
    <Dialog open={result !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogBackdrop />
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>{t("passwordTitle", { email: result?.user.email ?? "" })}</DialogTitle>
          <DialogDescription>{t("passwordHint")}</DialogDescription>
        </DialogHeader>
        <DialogBody>
          <div
            data-agent-hidden
            className="flex items-center gap-2 rounded-md bg-raised px-3 py-2 shadow-[inset_0_0_0_1px_var(--line-strong)]"
          >
            <code className="min-w-0 flex-1 truncate font-mono text-[13px] text-ink">
              {result?.temporaryPassword}
            </code>
            <Button
              type="button"
              size="icon-sm"
              variant="ghost"
              aria-label={t("copyPassword")}
              onClick={async () => {
                if (result && (await copy(result.temporaryPassword))) toast.success(t("copied"));
              }}
            >
              <Copy aria-hidden />
            </Button>
          </div>
        </DialogBody>
        <DialogFooter>
          <Button type="button" variant="primary" onClick={onClose}>
            {t("passwordDone")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
