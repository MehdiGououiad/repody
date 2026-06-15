import Link from "next/link";
import { ArrowRight, Database, Rocket, ShieldCheck } from "lucide-react";
import { getTranslations } from "next-intl/server";
import { Button } from "@/components/ui/button";

const STEPS = [
  { icon: Database, key: "extract" as const },
  { icon: ShieldCheck, key: "rules" as const },
  { icon: Rocket, key: "upload" as const },
] as const;

export async function GetStartedPanel({ show }: { show: boolean }) {
  if (!show) return null;

  const [t, tSteps, tCommon] = await Promise.all([
    getTranslations("dashboard.getStarted"),
    getTranslations("workflows.builder.steps"),
    getTranslations("common"),
  ]);

  return (
    <section className="panel-elevated rounded-xl border border-accent-blue/25 bg-accent-blue/5 overflow-hidden">
      <div className="px-5 py-4 border-b border-accent-blue/15">
        <h2 className="font-display text-base font-semibold text-on-surface">{t("title")}</h2>
        <p className="text-sm text-on-surface-variant mt-1 leading-relaxed">{t("description")}</p>
      </div>
      <ol className="grid gap-0 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-border/80">
        {STEPS.map(({ icon: Icon, key }, index) => (
          <li key={key} className="px-5 py-4 flex gap-3">
            <div className="size-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
              <Icon className="h-4 w-4" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
                {t("stepLabel", { number: index + 1 })}
              </p>
              <p className="text-sm font-semibold text-on-surface mt-0.5">{tSteps(key)}</p>
              <p className="text-xs text-on-surface-variant mt-1 leading-relaxed">
                {tSteps(`${key}Hint` as "extractHint")}
              </p>
            </div>
          </li>
        ))}
      </ol>
      <div className="px-5 py-4 border-t border-accent-blue/15 flex flex-col sm:flex-row gap-2 sm:items-center sm:justify-between">
        <p className="text-xs text-on-surface-variant">{t("footerHint")}</p>
        <Link href="/workflows/new">
          <Button size="sm" className="gap-2 w-full sm:w-auto">
            {tCommon("newWorkflow")}
            <ArrowRight className="h-4 w-4" />
          </Button>
        </Link>
      </div>
    </section>
  );
}
