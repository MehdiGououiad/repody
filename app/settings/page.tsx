import { Suspense } from "react";
import {
  fetchPlatformConfigServer,
  type PlatformConfig,
} from "@/lib/api/platform-config";
import { SettingsPageClient } from "./settings-client";

export default async function SettingsPage() {
  let platformConfig: PlatformConfig | null = null;
  let platformError: string | null = null;

  try {
    platformConfig = await fetchPlatformConfigServer();
  } catch (e) {
    platformError = e instanceof Error ? e.message : "Failed to load";
  }

  return (
    <Suspense fallback={<div className="panel-elevated rounded-xl h-64 animate-pulse m-6" />}>
      <SettingsPageClient
        platformConfig={platformConfig}
        platformError={platformError}
      />
    </Suspense>
  );
}
