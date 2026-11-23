import { getTranslations } from "next-intl/server";
import { Page } from "@/components/layout/page";
import { AccessOverview } from "@/components/settings/access-overview";
import { PlatformOverview } from "@/components/settings/platform-overview";
import { fetchAccess, fetchPlatformConfig } from "@/lib/api/server";

export async function generateMetadata() {
  return { title: (await getTranslations("nav"))("settings") };
}

export default async function SettingsPage() {
  const [tNav, access] = await Promise.all([getTranslations("nav"), fetchAccess()]);
  const platform = access.permissions.includes("metrics:read") ? await fetchPlatformConfig() : null;
  return (
    <Page description={(await getTranslations("pageHints"))("settings")} title={tNav("settings")}>
      <div className="flex flex-col gap-8">
        <AccessOverview access={access} />
        {platform ? <PlatformOverview platform={platform} /> : null}
      </div>
    </Page>
  );
}
