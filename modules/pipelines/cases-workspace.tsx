"use client";

import { ArrowRight, GitCompareArrows, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input, Textarea } from "@/components/ui/input";
import { useHasModule } from "@/modules/core/entitlement-context";
import { createApproval, createCase, startPipeline, verifyAuditChain } from "./api";
import type { AuditChainVerification, PipelineStageInput } from "./types";

export function CasesWorkspace() {
  const router = useRouter();
  const t = useTranslations("cases");
  const hasIdp = useHasModule("idp");
  const hasFraud = useHasModule("fraud");

  const [externalRef, setExternalRef] = useState("");
  const [payloadText, setPayloadText] = useState('{"invoice": {"total": "1000.00"}}');
  const [workflowId, setWorkflowId] = useState("wf-invoices");
  const [enableFraudPre, setEnableFraudPre] = useState(hasFraud);
  const [enableIdp, setEnableIdp] = useState(hasIdp);
  const [enableFraudPost, setEnableFraudPost] = useState(hasFraud);
  const [enableFourEyes, setEnableFourEyes] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [auditChain, setAuditChain] = useState<AuditChainVerification | null>(null);

  async function handleCreateCase(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const parsed = JSON.parse(payloadText || "{}") as Record<string, unknown>;
      const createdCase = await createCase({
        external_ref: externalRef.trim() || null,
        input_payload: parsed,
      });

      let approvalId: string | undefined;
      if (enableFourEyes) {
        const apr = await createApproval({
          case_id: createdCase.id,
          stage_name: "four_eyes_gate",
          payload_snapshot: parsed,
        });
        approvalId = apr.id;
      }

      const stages: PipelineStageInput[] = [];
      if (hasFraud && enableFraudPre) stages.push({ kind: "fraud_pre_check" });
      if (hasIdp && enableIdp && workflowId.trim()) {
        stages.push({ kind: "idp", workflow_id: workflowId.trim() });
      }
      if (hasFraud && enableFraudPost) stages.push({ kind: "fraud_post_verify" });
      if (enableFourEyes && approvalId) {
        stages.push({ kind: "four_eyes_gate", approval_id: approvalId });
      }

      if (stages.length > 0) {
        await startPipeline(createdCase.id, stages);
      }
      const query = approvalId ? `?approvalId=${encodeURIComponent(approvalId)}` : "";
      router.push(`/cases/${createdCase.id}${query}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("createFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function handleVerifyAuditChain() {
    setError(null);
    try {
      setAuditChain(await verifyAuditChain());
    } catch (err) {
      setError(err instanceof Error ? err.message : t("verifyFailed"));
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-6 py-7">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-line pb-4">
        <div className="space-y-1">
          <h1 className="flex items-center gap-2 text-xl font-semibold tracking-tight text-ink">
            <GitCompareArrows className="size-5 text-accent-ink" aria-hidden />
            {t("title")}
          </h1>
          <p className="text-[13px] text-ink-3">{t("subtitle")}</p>
        </div>

        <Button variant="secondary" size="sm" onClick={handleVerifyAuditChain}>
          <ShieldCheck className="size-3.5 text-pass-ink" aria-hidden />
          <span>{t("verifyAuditChain")}</span>
        </Button>
      </header>

      {auditChain ? (
        <output className="block rounded-lg border border-line bg-raised px-4 py-2.5 text-xs text-ink-2">
          {auditChain.valid
            ? t("auditChainValid", { count: auditChain.checked_count })
            : t("auditChainBroken", { id: auditChain.first_broken_id ?? "unknown" })}
        </output>
      ) : null}

      <form
        onSubmit={handleCreateCase}
        className="flex flex-col gap-4 rounded-xl border border-line bg-raised p-5 shadow-panel"
      >
        <div className="grid gap-4 md:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="case-external-ref" className="text-xs font-medium text-ink-2">
              {t("externalRefLabel")}
            </label>
            <Input
              id="case-external-ref"
              value={externalRef}
              onChange={(e) => setExternalRef(e.target.value)}
              placeholder="CASE-2026-001"
            />
          </div>

          {hasIdp ? (
            <div className="flex flex-col gap-1.5">
              <label htmlFor="case-workflow-id" className="text-xs font-medium text-ink-2">
                {t("idpWorkflowLabel")}
              </label>
              <Input
                id="case-workflow-id"
                value={workflowId}
                onChange={(e) => setWorkflowId(e.target.value)}
                placeholder="wf-invoices"
              />
            </div>
          ) : null}
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="case-payload-json" className="text-xs font-medium text-ink-2">
            {t("payloadLabel")}
          </label>
          <Textarea
            id="case-payload-json"
            value={payloadText}
            onChange={(e) => setPayloadText(e.target.value)}
            className="min-h-24 font-mono text-xs"
          />
        </div>

        <fieldset className="flex flex-wrap gap-4 border-t border-line pt-3">
          <legend className="px-1 text-xs font-medium text-ink-3">{t("stagesLegend")}</legend>
          {hasFraud ? (
            <label htmlFor="stage-fraud-pre" className="flex items-center gap-2 text-xs text-ink-2">
              <Checkbox
                id="stage-fraud-pre"
                checked={enableFraudPre}
                onCheckedChange={(v) => setEnableFraudPre(Boolean(v))}
              />
              <span>{t("stageFraudPre")}</span>
            </label>
          ) : null}
          {hasIdp ? (
            <label htmlFor="stage-idp" className="flex items-center gap-2 text-xs text-ink-2">
              <Checkbox
                id="stage-idp"
                checked={enableIdp}
                onCheckedChange={(v) => setEnableIdp(Boolean(v))}
              />
              <span>{t("stageIdp")}</span>
            </label>
          ) : null}
          {hasFraud ? (
            <label
              htmlFor="stage-fraud-post"
              className="flex items-center gap-2 text-xs text-ink-2"
            >
              <Checkbox
                id="stage-fraud-post"
                checked={enableFraudPost}
                onCheckedChange={(v) => setEnableFraudPost(Boolean(v))}
              />
              <span>{t("stageFraudPost")}</span>
            </label>
          ) : null}
          <label htmlFor="stage-four-eyes" className="flex items-center gap-2 text-xs text-ink-2">
            <Checkbox
              id="stage-four-eyes"
              checked={enableFourEyes}
              onCheckedChange={(v) => setEnableFourEyes(Boolean(v))}
            />
            <span>{t("stageFourEyes")}</span>
          </label>
        </fieldset>

        {error ? (
          <p role="alert" className="text-xs text-fail-ink">
            {error}
          </p>
        ) : null}

        <div className="flex justify-end">
          <Button type="submit" variant="primary" size="md" disabled={busy}>
            <span>{busy ? t("launching") : t("launchCase")}</span>
            <ArrowRight className="size-3.5" aria-hidden />
          </Button>
        </div>
      </form>
    </div>
  );
}
