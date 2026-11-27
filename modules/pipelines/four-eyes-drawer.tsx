"use client";

import { Check, Copy, Lock, ShieldCheck, Undo2, XCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Tabs, TabsList, TabsPanel, TabsTab } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { submitCheckerDecision, submitMakerReview } from "./api";
import { evaluateFourEyesGuard } from "./helpers";
import type { ApprovalTask, FourEyesDecision } from "./types";

function parseOverrideValue(raw: string): unknown {
  const trimmed = raw.trim();
  if (!trimmed) return "";
  try {
    return JSON.parse(trimmed) as unknown;
  } catch {
    return raw;
  }
}

export function FourEyesDrawer({
  approval,
  currentActorSub,
  onUpdated,
}: {
  approval: ApprovalTask;
  currentActorSub: string | null;
  onUpdated: (next: ApprovalTask) => void;
}) {
  const t = useTranslations("cases");
  const [fieldPath, setFieldPath] = useState("");
  const [afterValue, setAfterValue] = useState("");
  const [overrideReason, setOverrideReason] = useState("");
  const [makerNote, setMakerNote] = useState("");
  const [checkerNote, setCheckerNote] = useState("");
  const [actorOverride, setActorOverride] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const effectiveActor = actorOverride.trim() || currentActorSub || "";
  const guard = evaluateFourEyesGuard(approval, effectiveActor);
  const devHeaders = actorOverride.trim() ? { "X-Dev-User": actorOverride.trim() } : undefined;

  async function handleCopyHash() {
    await navigator.clipboard.writeText(approval.payload_sha256);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  async function handleMakerSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const overrides =
        fieldPath.trim() && overrideReason.trim()
          ? [
              {
                field_path: fieldPath.trim(),
                after_value: parseOverrideValue(afterValue),
                reason: overrideReason.trim(),
              },
            ]
          : [];
      const updated = await submitMakerReview(
        approval.id,
        { overrides, note: makerNote.trim() },
        devHeaders,
      );
      setFieldPath("");
      setAfterValue("");
      setOverrideReason("");
      onUpdated(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function handleCheckerDecision(decision: FourEyesDecision) {
    setError(null);
    setBusy(true);
    try {
      const updated = await submitCheckerDecision(
        approval.id,
        { decision, note: checkerNote.trim() },
        devHeaders,
      );
      onUpdated(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("actionFailed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="flex flex-col gap-4 rounded-xl border border-line bg-raised p-4 shadow-panel">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line pb-3">
        <div>
          <h2 className="text-[15px] font-semibold text-ink">{t("fourEyesTitle")}</h2>
          <p className="text-xs text-ink-3">{approval.stage_name}</p>
        </div>
        <span className="rounded-full border border-line bg-panel px-2.5 py-0.5 font-mono text-xs text-ink">
          {approval.status}
        </span>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line bg-panel px-3 py-2 text-xs">
        <span className="text-ink-3">{t("payloadHash")}</span>
        <div className="flex items-center gap-2">
          <code className="font-mono text-ink-2">{approval.payload_sha256.slice(0, 18)}…</code>
          <Button
            variant="ghost"
            size="icon-xs"
            onClick={handleCopyHash}
            aria-label={t("copyHash")}
          >
            {copied ? <Check className="text-pass-ink" /> : <Copy />}
          </Button>
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="four-eyes-dev-actor" className="text-xs text-ink-3">
          {t("devActorLabel")}
        </label>
        <Input
          id="four-eyes-dev-actor"
          compact
          value={actorOverride}
          onChange={(e) => setActorOverride(e.target.value)}
          placeholder={currentActorSub || "checker-sub"}
        />
      </div>

      {approval.overrides.length > 0 ? (
        <div className="overflow-x-auto rounded-lg border border-line bg-panel">
          <table className="w-full text-start text-xs">
            <thead className="border-b border-line text-ink-3">
              <tr>
                <th className="px-3 py-2 text-start font-medium">{t("colField")}</th>
                <th className="px-3 py-2 text-start font-medium">{t("colBefore")}</th>
                <th className="px-3 py-2 text-start font-medium">{t("colAfter")}</th>
                <th className="px-3 py-2 text-start font-medium">{t("colReason")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {approval.overrides.map((ov) => (
                <tr key={ov.id}>
                  <td className="px-3 py-2 font-mono text-ink">{ov.field_path}</td>
                  <td className="px-3 py-2 font-mono text-ink-3">
                    {JSON.stringify(ov.before_value)}
                  </td>
                  <td className="px-3 py-2 font-mono text-pass-ink">
                    {JSON.stringify(ov.after_value)}
                  </td>
                  <td className="px-3 py-2 text-ink-2">{ov.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <Tabs
        defaultValue={guard.canCheck || approval.status === "waiting_checker" ? "checker" : "maker"}
      >
        <TabsList variant="segmented">
          <TabsTab value="maker">{t("tabMaker")}</TabsTab>
          <TabsTab value="checker">{t("tabChecker")}</TabsTab>
        </TabsList>

        <TabsPanel value="maker" className="pt-3">
          <form onSubmit={handleMakerSubmit} className="flex flex-col gap-3">
            <div className="grid gap-2 sm:grid-cols-2">
              <div className="flex flex-col gap-1">
                <label htmlFor="override-path" className="text-xs text-ink-3">
                  {t("overrideField")}
                </label>
                <Input
                  id="override-path"
                  compact
                  value={fieldPath}
                  onChange={(e) => setFieldPath(e.target.value)}
                  placeholder="invoice.total"
                  disabled={!guard.canMake || busy}
                />
              </div>
              <div className="flex flex-col gap-1">
                <label htmlFor="override-after" className="text-xs text-ink-3">
                  {t("overrideValue")}
                </label>
                <Input
                  id="override-after"
                  compact
                  value={afterValue}
                  onChange={(e) => setAfterValue(e.target.value)}
                  placeholder="1050.00"
                  disabled={!guard.canMake || busy}
                />
              </div>
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="override-reason" className="text-xs text-ink-3">
                {t("overrideReason")}
              </label>
              <Input
                id="override-reason"
                compact
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                placeholder={t("overrideReasonPlaceholder")}
                disabled={!guard.canMake || busy}
              />
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="maker-note" className="text-xs text-ink-3">
                {t("reviewNote")}
              </label>
              <Textarea
                id="maker-note"
                value={makerNote}
                onChange={(e) => setMakerNote(e.target.value)}
                disabled={!guard.canMake || busy}
              />
            </div>
            <Button type="submit" variant="primary" disabled={!guard.canMake || busy}>
              {t("submitToChecker")}
            </Button>
          </form>
        </TabsPanel>

        <TabsPanel value="checker" className="pt-3">
          <div className="flex flex-col gap-3">
            {guard.selfApprovalBlocked ? (
              <output className="flex items-start gap-2 rounded-lg border border-warn/40 bg-warn-wash p-3 text-xs text-warn-ink">
                <Lock className="mt-0.5 size-3.5 shrink-0" aria-hidden />
                <span>{t("selfApprovalBlocked")}</span>
              </output>
            ) : null}
            <div className="flex flex-col gap-1">
              <label htmlFor="checker-note" className="text-xs text-ink-3">
                {t("checkerNote")}
              </label>
              <Textarea
                id="checker-note"
                value={checkerNote}
                onChange={(e) => setCheckerNote(e.target.value)}
                disabled={!guard.canCheck || busy}
              />
            </div>
            <div className={cn("flex flex-wrap gap-2")}>
              <Button
                variant="primary"
                disabled={!guard.canCheck || busy}
                onClick={() => handleCheckerDecision("approved")}
              >
                <ShieldCheck className="size-3.5" aria-hidden />
                {t("approve")}
              </Button>
              <Button
                variant="secondary"
                disabled={!guard.canCheck || busy}
                onClick={() => handleCheckerDecision("returned_to_maker")}
              >
                <Undo2 className="size-3.5" aria-hidden />
                {t("returnToMaker")}
              </Button>
              <Button
                variant="danger"
                disabled={!guard.canCheck || busy}
                onClick={() => handleCheckerDecision("rejected")}
              >
                <XCircle className="size-3.5" aria-hidden />
                {t("reject")}
              </Button>
            </div>
          </div>
        </TabsPanel>
      </Tabs>

      {error ? (
        <p role="alert" className="text-xs text-fail-ink">
          {error}
        </p>
      ) : null}
    </section>
  );
}
