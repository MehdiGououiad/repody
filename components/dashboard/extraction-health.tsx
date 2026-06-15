import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { ArrowUpRight, BrainCircuit, CheckCircle2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { OcrDiagnostic } from "@/lib/api/dashboard";

export async function ExtractionHealth({ ocr }: { ocr: OcrDiagnostic | null }) {
  const t = await getTranslations("dashboard.extraction");

  if (!ocr) return null;

  return (
    <section className="panel-elevated rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-border flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-base font-semibold text-on-surface">{t("title")}</h2>
          <p className="text-xs text-on-surface-variant mt-0.5">{t("hint")}</p>
        </div>
        <Link href="/settings?tab=models">
          <Button variant="ghost" size="sm" className="h-8 gap-1.5 text-xs">
            {t("manageModels")}
            <ArrowUpRight className="h-3.5 w-3.5" />
          </Button>
        </Link>
      </div>
      <div className="p-5 grid gap-4 sm:grid-cols-2">
        <div className="flex items-start gap-3">
          <div
            className={`size-10 rounded-lg flex items-center justify-center shrink-0 ${
              ocr.ok ? "bg-success/10 text-success" : "bg-danger/10 text-danger"
            }`}
          >
            {ocr.ok ? (
              <CheckCircle2 className="h-5 w-5" aria-hidden="true" />
            ) : (
              <XCircle className="h-5 w-5" aria-hidden="true" />
            )}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-on-surface">{ocr.model || t("unknownModel")}</p>
            <p className="text-xs text-on-surface-variant mt-0.5">{ocr.detail}</p>
            {ocr.hint ? (
              <p className="text-[11px] text-on-surface-variant/80 mt-2 leading-relaxed">{ocr.hint}</p>
            ) : null}
          </div>
        </div>
        <div className="flex flex-wrap gap-2 content-start">
          <Badge variant={ocr.inferenceReachable ? "success" : "danger"}>
            {ocr.inferenceReachable ? t("runtimeUp") : t("runtimeDown")}
          </Badge>
          <Badge variant={ocr.modelLoaded ? "success" : "outline"}>
            {ocr.modelLoaded ? t("modelLoaded") : t("modelNotLoaded")}
          </Badge>
          {ocr.runtime ? (
            <Badge variant="outline" className="gap-1">
              <BrainCircuit className="h-3 w-3" />
              {ocr.runtime}
            </Badge>
          ) : null}
        </div>
      </div>
    </section>
  );
}
