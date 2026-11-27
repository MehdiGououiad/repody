"use client";

import { ArrowLeft, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { createApproval, fetchApproval } from "./api";
import { FourEyesDrawer } from "./four-eyes-drawer";
import type { ApprovalTask, CaseRecord } from "./types";

export function CaseInspector({
  initialCase,
  initialApproval,
  currentActorSub,
}: {
  initialCase: CaseRecord;
  initialApproval: ApprovalTask | null;
  currentActorSub: string | null;
}) {
  const t = useTranslations("cases");
  const [approval, setApproval] = useState<ApprovalTask | null>(initialApproval);
  const [creating, setCreating] = useState(false);

  async function handleOpenCheckpoint() {
    setCreating(true);
    try {
      const created = await createApproval({
        case_id: initialCase.id,
        stage_name: "four_eyes_gate",
        payload_snapshot: initialCase.input_payload,
      });
      setApproval(await fetchApproval(created.id));
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-7">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-line pb-4">
        <div className="space-y-1">
          <Link
            href="/cases"
            className="inline-flex items-center gap-1.5 text-xs text-ink-3 hover:text-ink"
          >
            <ArrowLeft className="size-3.5" aria-hidden />
            <span>{t("backToCases")}</span>
          </Link>
          <h1 className="text-xl font-semibold tracking-tight text-ink">
            {initialCase.external_ref || initialCase.id}
          </h1>
          <p className="font-mono text-xs text-ink-3">
            {initialCase.id} · {approval?.status ?? initialCase.status}
          </p>
        </div>

        {!approval ? (
          <Button variant="primary" size="sm" disabled={creating} onClick={handleOpenCheckpoint}>
            <ShieldCheck className="size-3.5" aria-hidden />
            <span>{t("openCheckpoint")}</span>
          </Button>
        ) : null}
      </header>

      <div className="grid gap-5 lg:grid-cols-[1fr_1.15fr]">
        <section className="flex flex-col gap-3 rounded-xl border border-line bg-raised p-4 shadow-panel">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-ink-3">
            {t("casePayload")}
          </h2>
          <pre className="max-h-96 overflow-auto rounded-lg border border-line bg-canvas p-3 font-mono text-xs text-ink">
            {JSON.stringify(approval?.payload_snapshot ?? initialCase.input_payload, null, 2)}
          </pre>
        </section>

        {approval ? (
          <FourEyesDrawer
            approval={approval}
            currentActorSub={currentActorSub}
            onUpdated={setApproval}
          />
        ) : (
          <div className="flex min-h-48 items-center justify-center rounded-xl border border-dashed border-line bg-canvas/40 p-6 text-xs text-ink-3">
            {t("noCheckpoint")}
          </div>
        )}
      </div>
    </div>
  );
}
