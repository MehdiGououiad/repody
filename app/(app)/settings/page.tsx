import { getTranslations } from "next-intl/server";
import { PageHeader } from "@/components/layout/page-header";
import { PageShell } from "@/components/layout/page-shell";
import { PlatformOverview } from "@/components/settings/platform-overview";
import { fetchPlatformConfig } from "@/lib/api/server";

export default async function SettingsPage() {
  const [t, platform] = await Promise.all([getTranslations("settings"), fetchPlatformConfig()]);
  return (
    <PageShell>
      <PageHeader title={t("title")} description={t("description")} eyebrow={t("eyebrow")} />
      <PlatformOverview platform={platform} />
    </PageShell>
  );
}
