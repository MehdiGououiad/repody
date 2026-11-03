import { PageHeader } from "@/components/layout/page-header";
import { PageShell } from "@/components/layout/page-shell";
import { PlatformOverview } from "@/components/settings/platform-overview";
import { serverApi } from "@/lib/api/openapi-server";
import { fetchPlatformConfigServer } from "@/lib/api/platform-config-server";

export default async function SettingsPage() {
  const [platform, catalog] = await Promise.allSettled([
    fetchPlatformConfigServer(),
    serverApi.GET("/v1/models/catalog").then(({ data }) => data ?? null),
  ]);

  return (
    <PageShell>
      <PageHeader
        title="Platform"
        description="Runtime configuration and document model status."
        eyebrow="Settings"
      />
      {platform.status === "fulfilled" ? (
        <PlatformOverview
          platform={platform.value}
          catalog={catalog.status === "fulfilled" ? catalog.value : null}
        />
      ) : (
        <div className="rounded-xl border border-danger/30 bg-danger-soft p-4 text-sm text-danger">
          {platform.reason instanceof Error ? platform.reason.message : "Failed to load"}
        </div>
      )}
    </PageShell>
  );
}
