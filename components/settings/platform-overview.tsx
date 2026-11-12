import { getLocale, getTranslations } from "next-intl/server";
import { Section } from "@/components/layout/page";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { currentBrand } from "@/lib/theme/brand";
import type { PlatformConfig } from "@/lib/types";
import { formatBytes } from "@/lib/utils";

function Rows({ rows }: { rows: [string, React.ReactNode][] }) {
  return (
    <dl className="divide-y divide-line overflow-hidden rounded-lg shadow-[0_0_0_1px_var(--line)]">
      {rows.map(([label, value]) => (
        <div
          key={label}
          className="flex min-h-11 flex-wrap items-center justify-between gap-x-6 gap-y-1 px-4 py-2.5"
        >
          <dt className="text-sm text-ink-2">{label}</dt>
          <dd className="min-w-0 break-words text-end text-sm text-ink">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

const Swatch = ({ color }: { color: string }) => (
  <span className="inline-flex items-center gap-2 font-mono text-xs text-ink-3">
    <span
      className="size-3.5 rounded-sm shadow-[inset_0_0_0_1px_var(--line-strong)]"
      style={{ background: color }}
    />
    {color}
  </span>
);

/** Read-only: the deployment's brand, the model, and the runtime limits in effect. */
export async function PlatformOverview({ platform }: { platform: PlatformConfig }) {
  const [t, locale] = await Promise.all([getTranslations("settings"), getLocale()]);
  const brand = currentBrand();
  const model =
    platform.modelAvailable === null ? (
      <span className="inline-flex items-center gap-2">
        <StatusGlyph status="waiting" />
        {t("onDemand")}
      </span>
    ) : (
      <span className="inline-flex items-center gap-2">
        <StatusGlyph status={platform.modelAvailable ? "passed" : "failed"} />
        {platform.modelAvailable ? t("ready") : t("unavailable")}
      </span>
    );

  return (
    <div className="flex max-w-3xl flex-col gap-10">
      <Section title={t("modelTitle")} hint={t("modelHint")}>
        <Rows
          rows={[
            [t("model"), model],
            [
              t("servedModel"),
              <span key="m" className="font-mono text-xs">
                {platform.servedModel}
              </span>,
            ],
            [
              t("endpoint"),
              <span key="e" className="font-mono text-xs">
                {platform.llamacppBaseUrl}
              </span>,
            ],
            [t("cache"), platform.cacheEnabled ? t("enabled") : t("disabled")],
          ]}
        />
      </Section>

      <Section title={t("runtimeTitle")} hint={t("runtimeHint")}>
        <Rows
          rows={[
            [t("pagesPerDocument"), platform.maxPagesPerDocument ?? t("allPages")],
            [
              t("uploadLimit"),
              t("uploadLimitValue", {
                files: platform.maxUploadFiles,
                size: formatBytes(platform.maxUploadBytes, locale),
              }),
            ],
            [t("runTimeout"), t("minutes", { count: platform.runTimeoutMinutes })],
          ]}
        />
      </Section>

      <Section title={t("brandTitle")} hint={t("brandHint")}>
        <Rows
          rows={[
            [t("brandName"), brand.name],
            [t("brandBase"), <Swatch key="b" color={brand.base} />],
            [t("brandAccent"), <Swatch key="a" color={brand.accent} />],
            [t("brandContrast"), brand.contrast],
            [t("brandRadius"), `${brand.radius}px`],
          ]}
        />
      </Section>
    </div>
  );
}
