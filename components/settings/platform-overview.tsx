import { getLocale, getTranslations } from "next-intl/server";
import { Section } from "@/components/layout/page";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { currentBrand } from "@/lib/theme/brand";
import type { PlatformConfig } from "@/lib/types";
import { formatBytes } from "@/lib/utils";

function Rows({ rows }: { rows: [string, React.ReactNode][] }) {
  return (
    <dl className="divide-y divide-line overflow-hidden rounded-lg bg-panel shadow-[0_0_0_1px_var(--line)]">
      {rows.map(([label, value]) => (
        <div
          key={label}
          className="flex min-h-9 flex-wrap items-center justify-between gap-x-6 gap-y-1 px-3.5 py-1.5"
        >
          <dt className="text-[13px] text-ink-3">{label}</dt>
          <dd className="min-w-0 truncate text-end text-[13px] text-ink">{value}</dd>
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
      <span className="inline-flex h-5 items-center gap-1.5 rounded-full bg-accent-wash px-2 text-xs font-medium text-accent-ink">
        <span className="size-1.5 rounded-full bg-accent" aria-hidden />
        {t("onDemand")}
      </span>
    ) : (
      <span
        className={`inline-flex h-5 items-center gap-1.5 rounded-full px-2 text-xs font-medium ${
          platform.modelAvailable ? "bg-pass-wash text-pass-ink" : "bg-fail-wash text-fail-ink"
        }`}
      >
        <StatusGlyph status={platform.modelAvailable ? "passed" : "failed"} className="size-3" />
        {platform.modelAvailable ? t("ready") : t("unavailable")}
      </span>
    );

  return (
    <div className="grid grid-cols-1 gap-8 xl:grid-cols-2">
      <div className="flex flex-col gap-8">
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
      </div>
      <div className="flex flex-col gap-8">
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
        <Section title={t("palette")} hint={t("paletteHint")}>
          <div className="flex flex-col gap-4 rounded-lg bg-panel p-4 shadow-[0_0_0_1px_var(--line)]">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-ink-3 w-28">{t("actions")}</span>
              <span className="inline-flex h-7 items-center rounded-md bg-accent px-3 text-[13px] font-medium text-on-accent">
                {brand.name}
              </span>
              <span className="inline-flex h-7 items-center rounded-md bg-accent-wash px-3 text-[13px] font-medium text-accent-ink">
                {brand.name}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-xs text-ink-3 w-28">{t("status")}</span>
              {(["passed", "warning", "failed"] as const).map((status) => (
                <StatusGlyph key={status} status={status} className="size-4" />
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-ink-3 w-28">{t("documents")}</span>
              {[
                "bg-doc-1",
                "bg-doc-2",
                "bg-doc-3",
                "bg-doc-4",
                "bg-doc-5",
                "bg-doc-6",
                "bg-doc-7",
                "bg-doc-8",
              ].map((color) => (
                <span key={color} className={`size-4 rounded-[4px] ${color}`} aria-hidden />
              ))}
            </div>
          </div>
        </Section>
      </div>
    </div>
  );
}
