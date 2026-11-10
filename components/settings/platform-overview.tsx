import { BrainCircuit, Gauge, type LucideIcon } from "lucide-react";
import { getLocale, getTranslations } from "next-intl/server";
import type { PlatformConfig } from "@/lib/types";
import { formatBytes } from "@/lib/utils";

function MetricCard({
  label,
  value,
  detail,
  Icon,
}: {
  label: string;
  value: string;
  detail: string;
  Icon: LucideIcon;
}) {
  return (
    <div className="panel-elevated rounded-xl p-5 min-w-0">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-on-surface-variant">
          {label}
        </p>
        <span className="size-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
          <Icon className="h-4 w-4" aria-hidden="true" />
        </span>
      </div>
      <p className="mt-4 text-2xl font-display font-semibold text-on-surface truncate">{value}</p>
      <p className="mt-1 text-xs text-on-surface-variant">{detail}</p>
    </div>
  );
}

/** Read-only platform configuration and document-model status (no operator actions). */
export async function PlatformOverview({ platform }: { platform: PlatformConfig }) {
  const [t, locale] = await Promise.all([getTranslations("settings"), getLocale()]);
  const rows = [
    [t("endpoint"), platform.llamacppBaseUrl],
    [t("servedModel"), platform.servedModel],
    [t("pagesPerDocument"), platform.maxPagesPerDocument ?? t("allPages")],
    [
      t("uploadLimit"),
      t("uploadLimitValue", {
        files: platform.maxUploadFiles,
        size: formatBytes(platform.maxUploadBytes, locale),
      }),
    ],
    [t("runTimeout"), t("minutes", { count: platform.runTimeoutMinutes })],
  ] as const;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label={t("model")}
          value={platform.modelAvailable ? t("ready") : t("unavailable")}
          detail={platform.servedModel}
          Icon={BrainCircuit}
        />
        <MetricCard
          label={t("cache")}
          value={platform.cacheEnabled ? t("enabled") : t("disabled")}
          detail={t("cacheDetail")}
          Icon={Gauge}
        />
      </div>

      <section className="panel-elevated rounded-xl overflow-hidden">
        <div className="px-6 py-5 border-b border-border bg-surface-container-low">
          <h2 className="font-display text-lg font-semibold">{t("runtimeTitle")}</h2>
          <p className="text-sm text-on-surface-variant mt-1">{t("runtimeHint")}</p>
        </div>
        <dl className="grid sm:grid-cols-2 xl:grid-cols-3">
          {rows.map(([label, value]) => (
            <div key={label} className="px-6 py-4 border-b border-r border-border/70">
              <dt className="text-[11px] uppercase tracking-wider text-on-surface-variant">
                {label}
              </dt>
              <dd className="font-mono text-sm mt-1 break-words">{value}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}
