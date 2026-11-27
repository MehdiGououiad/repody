"use client";

import { ArrowRight, FileSearch, GitCompareArrows, ShieldAlert, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { buttonVariants } from "@/components/ui/button";
import { useEntitlements, useHasModule } from "./entitlement-context";

/** Clean launcher presenting strictly licensed modules and end-to-end orchestration. */
export function HubLauncher() {
  const entitlements = useEntitlements();
  const hasIdp = useHasModule("idp");
  const hasFraud = useHasModule("fraud");
  const t = useTranslations("workspaces");

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-6 py-8">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-line pb-5">
        <div className="space-y-1">
          <h1 className="text-xl font-semibold tracking-tight text-ink">{t("hubTitle")}</h1>
          <p className="text-[13px] text-ink-3">{t("hubSubtitle")}</p>
        </div>
        <div className="inline-flex items-center gap-2 rounded-full border border-line bg-raised px-3 py-1 text-xs font-medium text-ink-2">
          <ShieldCheck className="size-3.5 text-pass" aria-hidden />
          <span>{entitlements.status === "grace" ? t("licenseGrace") : t("licenseActive")}</span>
        </div>
      </header>

      {entitlements.warning ? (
        <output className="block rounded-lg border border-warn/40 bg-warn-wash px-4 py-3 text-[13px] text-ink">
          {entitlements.warning}
        </output>
      ) : null}

      <section className="grid gap-4 md:grid-cols-2">
        {hasIdp ? (
          <article className="flex flex-col justify-between gap-4 rounded-xl border border-line bg-raised p-5 shadow-panel">
            <div className="space-y-2">
              <div className="flex size-9 items-center justify-center rounded-lg bg-accent/15 text-accent-ink">
                <FileSearch className="size-4" aria-hidden />
              </div>
              <h2 className="text-[15px] font-semibold text-ink">{t("idp")}</h2>
              <p className="text-[13px] leading-relaxed text-ink-3">{t("idpDesc")}</p>
            </div>
            <Link
              href="/dashboard"
              className={buttonVariants({ variant: "secondary", size: "sm" })}
            >
              <span>{t("openWorkspace")}</span>
              <ArrowRight className="size-3.5" aria-hidden />
            </Link>
          </article>
        ) : null}

        {hasFraud ? (
          <article className="flex flex-col justify-between gap-4 rounded-xl border border-line bg-raised p-5 shadow-panel">
            <div className="space-y-2">
              <div className="flex size-9 items-center justify-center rounded-lg bg-fail-wash text-fail-ink">
                <ShieldAlert className="size-4" aria-hidden />
              </div>
              <h2 className="text-[15px] font-semibold text-ink">{t("fraud")}</h2>
              <p className="text-[13px] leading-relaxed text-ink-3">{t("fraudDesc")}</p>
            </div>
            <Link href="/fraud" className={buttonVariants({ variant: "secondary", size: "sm" })}>
              <span>{t("openWorkspace")}</span>
              <ArrowRight className="size-3.5" aria-hidden />
            </Link>
          </article>
        ) : null}
      </section>

      <section className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-line bg-panel p-5 shadow-panel">
        <div className="flex items-start gap-3">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-selected text-ink">
            <GitCompareArrows className="size-4" aria-hidden />
          </div>
          <div className="space-y-1">
            <h2 className="text-[15px] font-semibold text-ink">{t("pipelinesTitle")}</h2>
            <p className="max-w-2xl text-[13px] text-ink-3">{t("pipelinesDesc")}</p>
          </div>
        </div>
        <Link href="/cases" className={buttonVariants({ variant: "primary", size: "md" })}>
          <span>{t("cases")}</span>
          <ArrowRight className="size-3.5" aria-hidden />
        </Link>
      </section>
    </div>
  );
}
