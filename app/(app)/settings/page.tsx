import { getTranslations } from "next-intl/server";
import { Page } from "@/components/layout/page";
import { PlatformOverview } from "@/components/settings/platform-overview";
import { fetchPlatformConfig } from "@/lib/api/server";

export async function generateMetadata() {
  return { title: (await getTranslations("nav"))("settings") };
}

export default async function SettingsPage() {
  const [tNav, platform] = await Promise.all([getTranslations("nav"), fetchPlatformConfig()]);
  return (
    <Page title={tNav("settings")}>
      <PlatformOverview platform={platform} />
    </Page>
  );
}
